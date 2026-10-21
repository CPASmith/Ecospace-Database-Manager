import streamlit as st
import pandas as pd
from ui.edit_taxa import show_editable_table
from ui.bulk_edit_taxa import select_my_data_to_modify, definir_parametres_ecologiques
from utils import rename_map, preferred_order
from ui.ecologie_schema import generer_schema_ecologique

# Explore écologie sélection d’un taxon
if st.session_state.get("selected_taxon_id"):
    generer_schema_ecologique(st.session_state["selected_taxon_id"], cursor)

def show_explorer(conn, cursor):
    st.markdown("## 📜 Liste des my_data")
    if "mode_modification_multiple" not in st.session_state:
        st.session_state["mode_modification_multiple"] = False

    # --- Initialisation des filtres ---
    cursor.execute("SELECT * FROM my_data LIMIT 1;")
    all_columns = [desc[0] for desc in cursor.description]

    if "active_filters" not in st.session_state:
        st.session_state["active_filters"] = {}
    if "enable_filter" not in st.session_state:
        st.session_state["enable_filter"] = False

    # --- Filtres actifs ---
    if st.session_state["active_filters"]:
        st.markdown("### 🎯 Filtres actifs")
        for col, val in st.session_state["active_filters"].items():
            st.markdown(f"- **{col}** = `{val}`")

    with st.expander("➕ Ajouter un filtre", expanded=not st.session_state["active_filters"]):
        # Appliquer le renommage et l’ordre préféré
        reverse_map = {v: k for k, v in rename_map.items()}
        renamed_cols = [rename_map.get(col, col) for col in all_columns]

        # Tri selon l’ordre préféré
        ordered_cols = [col for col in preferred_order if col in renamed_cols]
        remaining_cols = [col for col in renamed_cols if col not in ordered_cols]
        final_cols = ordered_cols + remaining_cols

        col_to_filter_display = st.selectbox("Choisissez une variable", ["(Aucune)"] + final_cols, key="filter_col")
        
        if col_to_filter_display and col_to_filter_display != "(Aucune)":
            col_to_filter = reverse_map.get(col_to_filter_display, col_to_filter_display)

            cursor.execute(f'SELECT DISTINCT "{col_to_filter}" FROM my_data WHERE "{col_to_filter}" IS NOT NULL;')
            values = sorted([row[0] for row in cursor.fetchall() if row[0]])
            selected_value = st.selectbox(
                f"value pour {col_to_filter}",
                ["(Aucune)"] + values,
                key=f"filter_val_{col_to_filter}"
            )
            if st.button("✅ Ajouter ce filtre") and selected_value != "(Aucune)":
                st.session_state["active_filters"][col_to_filter] = selected_value
                st.session_state["enable_filter"] = True
                st.rerun()

    if st.session_state["active_filters"]:
        if st.button("❌ Retirer tous les filtres"):
            st.session_state["active_filters"] = {}
            st.session_state["enable_filter"] = False
            st.rerun()

    # --- Requête filtrée ---
    query = "SELECT * FROM my_data"
    params = []
    if st.session_state["enable_filter"] and st.session_state["active_filters"]:
        clauses = []
        for col, val in st.session_state["active_filters"].items():
            clauses.append(f"{col} = %s")
            params.append(val)
        query += " WHERE " + " AND ".join(clauses)
    
    query += " ORDER BY id"
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(rows, columns=columns)
    
    if "id" in df.columns:
        df.set_index("id", inplace=True)
        
        
    df.columns = [col.lower() for col in df.columns]  # normaliser la casse
    df.rename(columns=rename_map, inplace=True)

    
    actual = df.columns.tolist()
    ordered = [col for col in preferred_order if col in actual]
    remaining = [col for col in actual if col not in ordered]
    df = df[ordered + remaining]

    # --- Affichage final ---
    st.dataframe(df, use_container_width=True)
    
    if st.checkbox("🖊️ Activer le mode édition"):
        from ui.edit_taxa import show_editable_table
        show_editable_table(df, conn, cursor)

    # --- Lancer le mode modification multiple ---
    if st.button("⚙️ Modifier plusieurs my_data par lot"):
        st.session_state["mode_modification_multiple"] = True

    # --- Étape 1 : sélection des my_data ---
    if st.session_state.get("mode_modification_multiple") and "my_data_cibles" not in st.session_state:
        if select_my_data_to_modify(cursor):
            nb = len(st.session_state.get("my_data_cibles_temp", []))
            if nb:
                st.success(f"🎯 {nb} occurrence(s) sélectionnée(s).")
                if st.button("✅ Valider la sélection"):
                    st.session_state["my_data_cibles"] = st.session_state["my_data_cibles_temp"]
                    st.session_state["validation_parametres_eco"] = True
                    st.rerun()

    # --- Étape 2 : validation explicite ---
        if "my_data_cibles" in st.session_state:
            if st.button("✅ Valider la sélection"):
                st.session_state["my_data_cibles"] = st.session_state.get("my_data_cibles_temp", [])
                st.session_state["validation_parametres_eco"] = True
                st.rerun()

    # --- Étape 3 : affichage des paramètres écologiques ---
    if st.session_state.get("validation_parametres_eco"):
        from ui.bulk_edit_taxa import definir_parametres_ecologiques
        definir_parametres_ecologiques(conn, cursor)

    # --- Bouton d'annulation complet ---
    if st.session_state.get("mode_modification_multiple"):
        if st.button("🔙 Annuler la modification multiple"):
            for key in [
                "mode_modification_multiple",
                "bulk_filter_col",
                "bulk_filter_val",
                "bulk_selected_col",
                "bulk_selected_val",
                "my_data_cibles",
                "parametres_eco",
                "dimensions_immediates",
                "validation_parametres_eco"
            ]:
                st.session_state.pop(key, None)
            st.rerun()
