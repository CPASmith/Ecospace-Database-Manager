import streamlit as st
import numpy as np
from utils import rename_map, preferred_order, supprimer_dimensions_incompatibles

def convert_to_native(value):
    import numpy as np
    import math

    # numpy scalar → python scalar
    if isinstance(value, np.generic):
        value = value.item()

    # NaN → NULL (PostgreSQL)
    if value is None:
        return None

    if isinstance(value, float) and math.isnan(value):
        return None

    return value



def show_editable_table(df, conn, cursor):
    st.markdown("### ✏️ Mode édition activé")

    reverse_map = {v: k for k, v in rename_map.items()}

    display_df = df.copy()
    display_df.rename(columns=rename_map, inplace=True)
    edited_df = st.data_editor(display_df, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    updated_rows = 0

    if st.button("💾 Enregistrer les modifications"):
        try:
            # Une transaction unique : en cas d'erreur, aucune modification
            # (ni de my_data ni des réponses contextuelles) n'est validée.
            for i in range(min(len(df), len(edited_df))):
                original_row = display_df.iloc[i]
                edited_row = edited_df.iloc[i]
                update_columns = []
                update_values = []

                for col in display_df.columns:
                    old_value = convert_to_native(original_row[col])
                    new_value = convert_to_native(edited_row[col])
                    if old_value != new_value:
                        col_sql = reverse_map.get(col, col.lower())
                        if col_sql == "id":
                            raise ValueError("La modification de l'identifiant id n'est pas autorisée.")
                        update_columns.append(f'"{col_sql}" = %s')
                        update_values.append(new_value)

                if update_columns:
                    taxon_id = int(df.index[i])
                    cursor.execute(
                        f"UPDATE my_data SET {', '.join(update_columns)} WHERE id = %s",
                        tuple(update_values + [taxon_id]),
                    )
                    supprimer_dimensions_incompatibles(cursor, taxon_id)
                    updated_rows += 1

            conn.commit()
            if updated_rows:
                st.success(f"{updated_rows} ligne(s) mise(s) à jour.")
                st.rerun()
            else:
                st.info("Aucune modification détectée.")
        except Exception as e:
            conn.rollback()
            st.error(f"Erreur lors de l'enregistrement : {e}")
