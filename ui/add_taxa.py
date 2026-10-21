import streamlit as st
from collections import defaultdict
from utils import select_or_custom

ECO_FIELDS = ("tiering", "motility", "feeding", "size", "main_biomineralisation")


def _questions_applicables(cursor, params):
    """Return question choices for contexts whose ALL specified conditions match."""
    cursor.execute(
        """
        SELECT d.id, d.context_id, d.question, d.value
        FROM contextual_dimensions AS d
        JOIN contexts AS c ON c.id = d.context_id
        WHERE (c.tiering IS NULL OR c.tiering = %s)
          AND (c.motility IS NULL OR c.motility = %s)
          AND (c.feeding IS NULL OR c.feeding = %s)
          AND (c.size IS NULL OR c.size = %s)
          AND (c.main_biomineralisation IS NULL OR c.main_biomineralisation = %s)
        ORDER BY d.context_id, d.question, d.value, d.id
        """,
        tuple(params[f] or None for f in ECO_FIELDS),
    )
    grouped = defaultdict(list)
    for dim_id, context_id, question, value in cursor.fetchall():
        grouped[(context_id, question)].append((dim_id, value))
    return grouped


def show_add_form(conn, cursor):
    st.markdown("## ➕ Ajouter une donnée")

    cursor.execute("SELECT * FROM my_data LIMIT 0")
    colonnes = [desc[0] for desc in cursor.description]
    champs_generaux = [c for c in colonnes if c not in ECO_FIELDS and c not in ("id", "reference_to_ecology")]

    st.markdown("### 📋 Données générales")
    donnees = {}
    for champ in champs_generaux:
        cursor.execute(f'SELECT DISTINCT "{champ}" FROM my_data WHERE "{champ}" IS NOT NULL')
        options = [r[0] for r in cursor.fetchall() if r[0] is not None and r[0] != ""]
        donnees[champ] = select_or_custom(champ.replace("_", " ").capitalize(), options, key_prefix=f"champ_{champ}")

    st.markdown("---")
    st.markdown("### 🧬 Paramètres écologiques")
    params_eco = {}
    selected = []  # (dimension_id or None, context_id, question, response)

    # Afficher les questions directement sous le caractère qui les déclenche.
    # Pour les contextes à plusieurs conditions, on les place sous le dernier
    # caractère requis dans l'ordre d'affichage, une fois TOUTES les conditions remplies.
    for champ in ECO_FIELDS:
        cursor.execute(f'SELECT DISTINCT "{champ}" FROM my_data WHERE "{champ}" IS NOT NULL')
        options = [r[0] for r in cursor.fetchall() if r[0] is not None and r[0] != ""]
        params_eco[champ] = select_or_custom(champ.capitalize(), options, f"param_{champ}")

        if not params_eco[champ]:
            continue

        # Les autres champs non encore sélectionnés restent à NULL : un contexte
        # n'est applicable que si chacune de ses conditions non NULL correspond.
        cursor.execute(
            """
            SELECT d.id, d.context_id, d.question, d.value,
                   c.tiering, c.motility, c.feeding, c.size, c.main_biomineralisation
            FROM contextual_dimensions d
            JOIN contexts c ON c.id = d.context_id
            WHERE (c.tiering IS NULL OR c.tiering = %s)
              AND (c.motility IS NULL OR c.motility = %s)
              AND (c.feeding IS NULL OR c.feeding = %s)
              AND (c.size IS NULL OR c.size = %s)
              AND (c.main_biomineralisation IS NULL OR c.main_biomineralisation = %s)
            ORDER BY d.context_id, d.question, d.value, d.id
            """,
            tuple(params_eco.get(f) or None for f in ECO_FIELDS),
        )
        grouped = defaultdict(list)
        for dim_id, context_id, question, response_value, *conditions in cursor.fetchall():
            required = [f for f, condition in zip(ECO_FIELDS, conditions) if condition is not None]
            # Chaque question est affichée une seule fois, sous le dernier
            # champ requis. Les contextes sans condition sont traités à part.
            if not required or required[-1] != champ:
                continue
            grouped[(context_id, question)].append((dim_id, response_value))

        for (context_id, question), choices in grouped.items():
            # Même décalage visuel que dans bulk_edit_taxa.py.
            col1, col2 = st.columns([0.1, 0.9])
            with col2:
                values = sorted({response for _, response in choices})
                lookup = {response: dim_id for dim_id, response in choices}
                key = f"add_dim_{context_id}_{question}"
                response = select_or_custom(f"↳ {question}", values, key_prefix=f"{key}_1")
                if response:
                    selected.append((lookup.get(response), context_id, question, response))
                if st.checkbox("➕ Ajouter une autre valeur", key=f"{key}_extra"):
                    response2 = select_or_custom(
                        f"↳ {question} (valeur supplémentaire)", values, key_prefix=f"{key}_2"
                    )
                    if response2 and response2 != response:
                        selected.append((lookup.get(response2), context_id, question, response2))

    st.markdown("### 📚 Référence écologique")
    cursor.execute("SELECT DISTINCT reference_to_ecology FROM my_data WHERE reference_to_ecology IS NOT NULL")
    ref_options = [r[0] for r in cursor.fetchall() if r[0]]
    ref_value = select_or_custom("Reference to ecology", ref_options, key_prefix="ref_eco")
    st.markdown("---")

    if st.button("📂 Valider et enregistrer le taxon"):
        if not any(donnees.values()) or not all(params_eco.values()):
            st.warning("⚠️ Veuillez remplir au moins une donnée générale et tous les paramètres écologiques.")
            return
        try:
            # Single transaction: do not commit until the taxon AND its responses are saved.
            donnees["reference_to_ecology"] = ref_value or None
            fields = list(donnees) + list(ECO_FIELDS)
            values = [donnees[f] or None for f in donnees] + [params_eco[f] for f in ECO_FIELDS]
            cols_sql = ", ".join(f'"{f}"' for f in fields)
            placeholders = ", ".join(["%s"] * len(fields))
            cursor.execute(
                f"INSERT INTO my_data ({cols_sql}) VALUES ({placeholders}) RETURNING id",
                values,
            )
            taxon_id = cursor.fetchone()[0]

            # Preserve original behaviour: register the complete main-ecology context.
            cursor.execute(
                """
                INSERT INTO contexts (tiering, motility, feeding, size, main_biomineralisation)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT ON CONSTRAINT unique_context_combination DO NOTHING
                """,
                tuple(params_eco[f] for f in ECO_FIELDS),
            )

            for dim_id, context_id, question, response in selected:
                if dim_id is None:
                    # Custom option: reuse it if another user already created it.
                    cursor.execute(
                        """
                        SELECT id FROM contextual_dimensions
                        WHERE context_id = %s AND question = %s AND value = %s
                        ORDER BY id LIMIT 1
                        """,
                        (context_id, question, response),
                    )
                    row = cursor.fetchone()
                    if row:
                        dim_id = row[0]
                    else:
                        cursor.execute(
                            """
                            INSERT INTO contextual_dimensions (context_id, question, value)
                            VALUES (%s, %s, %s) RETURNING id
                            """,
                            (context_id, question, response),
                        )
                        dim_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    INSERT INTO contextual_values (taxon_id, contextual_dimensions_id, value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (taxon_id, contextual_dimensions_id) DO NOTHING
                    """,
                    (taxon_id, dim_id, response),
                )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            st.error(f"Erreur lors de l'ajout du taxon : {exc}")
            return
        st.success(f"🌿 Data ajouté avec succès ! ")
        # Do not rerun immediately: keep the success confirmation visible.
