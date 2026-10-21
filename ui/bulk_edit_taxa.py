import streamlit as st
from utils import select_or_custom, rename_map, preferred_order, supprimer_dimensions_incompatibles
from collections import defaultdict


def select_my_data_to_modify(cursor):
    st.markdown("### 🧪 Sélection des my_data à modifier")

    cursor.execute("SELECT * FROM my_data LIMIT 1")
    all_columns = [desc[0] for desc in cursor.description]

    reverse_map = {v: k for k, v in rename_map.items()}
    renamed_cols = [rename_map.get(col, col) for col in all_columns]
    ordered_cols = [col for col in preferred_order if col in renamed_cols]
    remaining_cols = [col for col in renamed_cols if col not in ordered_cols]
    final_cols = ordered_cols + remaining_cols

    selected_column_display = st.selectbox(
        "Filtrer par colonne", ["(Aucune)"] + final_cols, key="bulk_filter_col"
    )

    selected_column = None
    if selected_column_display and selected_column_display != "(Aucune)":
        selected_column = reverse_map.get(selected_column_display, selected_column_display)

    if selected_column and selected_column != "(Aucune)":
        cursor.execute(
            f'SELECT DISTINCT "{selected_column}" FROM my_data WHERE "{selected_column}" IS NOT NULL'
        )
        values = sorted([row[0] for row in cursor.fetchall()])

        if values:
            selected_value = st.selectbox("value ciblée", values, key="bulk_filter_val")

            if selected_value:
                st.session_state["bulk_selected_col"] = selected_column
                st.session_state["bulk_selected_val"] = selected_value

                cursor.execute(
                    f'SELECT id FROM my_data WHERE "{selected_column}" = %s',
                    (selected_value,),
                )
                ids = [row[0] for row in cursor.fetchall()]
                st.session_state["my_data_cibles_temp"] = ids
                return True

    return False


def _get_or_create_dimension_id(conn, cursor, question: str, reponse: str, values):
    """
    values: liste de tuples (dim_id, val) existants pour une question donnée.
    Si reponse existe déjà => retourne dim_id.
    Sinon => crée une nouvelle contextual_dimension en réutilisant le context_id
    d'une dimension existante de la même question, et retourne le nouvel id.
    """
    existing = next((did for did, val in values if val == reponse), None)
    if existing is not None:
        return existing

    if not values:
        st.error(
            f"Impossible de créer une nouvelle dimension pour '{question}' (aucune dimension existante)."
        )
        return None

    any_dim_id = values[0][0]
    cursor.execute("SELECT context_id FROM contextual_dimensions WHERE id = %s", (any_dim_id,))
    row = cursor.fetchone()
    if not row:
        st.error("Impossible de récupérer context_id pour créer la dimension.")
        return None

    context_id = row[0]

    cursor.execute(
        """
        INSERT INTO contextual_dimensions (context_id, question, value)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (context_id, question, reponse),
    )
    new_id = cursor.fetchone()[0]
    conn.commit()  # OK pour l'instant
    return new_id


def definir_parametres_ecologiques(conn, cursor):
    st.markdown("### 🧬 Définir les paramètres écologiques")

    col = st.session_state.get("bulk_selected_col")
    val = st.session_state.get("bulk_selected_val")
    if col and val:
        st.markdown(f"🧬 Modification en masse des my_data où **{col} = `{val}`**")

    parametres = {}
    reponses_dim_selectionnees = {}

    for champ in ["tiering", "motility", "feeding", "size", "main_biomineralisation"]:
        cursor.execute(f"SELECT DISTINCT {champ} FROM my_data WHERE {champ} IS NOT NULL")
        options = sorted([r[0] for r in cursor.fetchall() if r[0]])
        value = select_or_custom(champ.capitalize(), options, f"param_{champ}")
        parametres[champ] = value

        if not value:
            continue

        query = f"""
            SELECT DISTINCT dc.question, dc.id, dc.value
            FROM contextual_dimensions dc
            JOIN contexts c ON dc.context_id = c.id
            WHERE CAST(c."{champ}" AS TEXT) = %s
              AND c."{champ}" IS NOT NULL
        """
        cursor.execute(query, (str(value),))
        dims = cursor.fetchall()

        if not dims:
            st.info(f"Aucune dimension contextuelle liée uniquement à {champ} = '{value}'")
            continue

        grouped = defaultdict(list)
        for question, dim_id, val_dim in dims:
            grouped[question].append((dim_id, val_dim))

        for question, values in grouped.items():
            col1, col2 = st.columns([0.1, 0.9])
            with col2:
                options = [v for _, v in values]
                reponses = []

                reponse_1 = select_or_custom(
                    label=f"↳ {question}",
                    options=options,
                    key_prefix=f"dim_{champ}_{question}_1",
                )
                if reponse_1:
                    dim_id_1 = _get_or_create_dimension_id(conn, cursor, question, reponse_1, values)
                    if dim_id_1 is not None:
                        reponses.append((dim_id_1, reponse_1))

                if st.checkbox("➕ Ajouter une autre valeur", key=f"{champ}_{question}_checkbox"):
                    reponse_2 = select_or_custom(
                        label=f"↳ {question} (valeur supplémentaire)",
                        options=options,
                        key_prefix=f"dim_{champ}_{question}_2",
                    )
                    if reponse_2:
                        dim_id_2 = _get_or_create_dimension_id(conn, cursor, question, reponse_2, values)
                        if dim_id_2 is not None and (dim_id_2, reponse_2) not in reponses:
                            reponses.append((dim_id_2, reponse_2))

                for dim_id, val_dim in reponses:
                    reponses_dim_selectionnees[dim_id] = val_dim

    
    st.markdown("---")
    st.markdown("### 📚 Référence écologique")
    cursor.execute('SELECT DISTINCT reference_to_ecology FROM my_data WHERE reference_to_ecology IS NOT NULL')
    ref_options = [row[0] for row in cursor.fetchall() if row[0]]
    ref_value = select_or_custom("Reference to ecology", ref_options, key_prefix="ref_eco")
        
    
    # --- Enregistrement final ---
    st.session_state["parametres_eco"] = parametres
    st.session_state["reponses_dim_selectionnees"] = reponses_dim_selectionnees

    if all(parametres.values()) and st.session_state.get("my_data_cibles"):
        if st.button("📂 Enregistrer les modifications"):
            try:
                # 1) Création ou récupération du contexte principal
                cursor.execute("""
                    INSERT INTO contexts (tiering, motility, feeding, size, main_biomineralisation)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT ON CONSTRAINT unique_context_combination
                    DO NOTHING
                    RETURNING id;
                """, (
                    parametres["tiering"],
                    parametres["motility"],
                    parametres["feeding"],
                    parametres["size"],
                    parametres["main_biomineralisation"]
                ))
                res = cursor.fetchone()

                if res:
                    context_id = res[0]
                else:
                    cursor.execute("""
                        SELECT id FROM contexts
                        WHERE tiering = %s
                          AND motility = %s
                          AND feeding = %s
                          AND size = %s
                          AND main_biomineralisation = %s
                    """, (
                        parametres["tiering"],
                        parametres["motility"],
                        parametres["feeding"],
                        parametres["size"],
                        parametres["main_biomineralisation"]
                    ))
                    context_id = cursor.fetchone()[0]

                # 2) Regrouper les réponses sélectionnées par question
                reponses_par_question = defaultdict(list)

                for dim_id, value in reponses_dim_selectionnees.items():
                    cursor.execute(
                        "SELECT question FROM contextual_dimensions WHERE id = %s",
                        (dim_id,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        continue

                    question = row[0]
                    reponses_par_question[question].append((dim_id, value))

                # 3) Appliquer les modifications à chaque taxon sélectionné
                for taxon_id in st.session_state["my_data_cibles"]:

                    # 3a) Mise à jour des paramètres écologiques principaux
                    cursor.execute("""
                        UPDATE my_data
                        SET tiering = %s,
                            motility = %s,
                            feeding = %s,
                            size = %s,
                            main_biomineralisation = %s
                        WHERE id = %s
                    """, (
                        parametres["tiering"],
                        parametres["motility"],
                        parametres["feeding"],
                        parametres["size"],
                        parametres["main_biomineralisation"],
                        taxon_id
                    ))

                    # 3b) Mise à jour éventuelle de la référence écologique
                    if ref_value:
                        cursor.execute("""
                            UPDATE my_data
                            SET reference_to_ecology = %s
                            WHERE id = %s
                        """, (ref_value, taxon_id))

                    # 3c) Nettoyage commun aux deux interfaces, y compris avec NULL
                    supprimer_dimensions_incompatibles(cursor, taxon_id)

                    # 3d) Pour chaque question modifiée, supprimer une seule fois les anciennes réponses
                    # puis insérer toutes les nouvelles valeurs sélectionnées
                    for question, dims_vals in reponses_par_question.items():
                        cursor.execute("""
                            DELETE FROM contextual_values
                            WHERE taxon_id = %s
                              AND contextual_dimensions_id IN (
                                  SELECT id
                                  FROM contextual_dimensions
                                  WHERE question = %s
                              )
                        """, (taxon_id, question))

                        for dim_id, value in dims_vals:
                            cursor.execute("""
                                INSERT INTO contextual_values (taxon_id, contextual_dimensions_id, value)
                                VALUES (%s, %s, %s)
                            """, (taxon_id, dim_id, value))

                conn.commit()
                st.success("✅ Modifications enregistrées pour tous les my_data sélectionnés.")
                st.balloons()
                st.rerun()

            except Exception as e:
                conn.rollback()
                st.error(f"Erreur lors de l'enregistrement des modifications : {e}")

__all__ = ["select_my_data_to_modify", "definir_parametres_ecologiques"]