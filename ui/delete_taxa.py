"""Filtered, confirmation-gated deletion of occurrences and their contextual answers."""
import pandas as pd
import streamlit as st
from psycopg2 import sql
from utils import rename_map, preferred_order


def show_deletion_interface(conn, cursor):
    st.markdown('## 🗑️ Supprimer des my_data')
    st.caption('Filtrez les occurrences, cochez celles à supprimer, puis confirmez explicitement.')

    prefix = 'delete_taxa_v2_'
    filters_key = prefix + 'filters'
    if filters_key not in st.session_state:
        st.session_state[filters_key] = {}

    cursor.execute('SELECT * FROM my_data LIMIT 0')
    all_columns = [description[0] for description in cursor.description]
    reverse_map = {rename_map.get(c, c): c for c in all_columns}
    display_cols = list(reverse_map)
    ordered = [c for c in preferred_order if c in display_cols]
    display_cols = ordered + [c for c in display_cols if c not in ordered]

    active_filters = st.session_state[filters_key]
    if active_filters:
        st.markdown('### 🎯 Filtres actifs')
        for col, value in active_filters.items():
            st.write(f'**{rename_map.get(col, col)}** = `{value}`')

    with st.expander('➕ Ajouter un filtre', expanded=not bool(active_filters)):
        display_col = st.selectbox('Choisissez une variable', ['(Aucune)'] + display_cols, key=prefix + 'column')
        if display_col != '(Aucune)':
            column = reverse_map[display_col]
            cursor.execute(
                sql.SQL('SELECT DISTINCT {} FROM my_data WHERE {} IS NOT NULL ORDER BY {}').format(
                    sql.Identifier(column), sql.Identifier(column), sql.Identifier(column)
                )
            )
            values = [row[0] for row in cursor.fetchall()]
            # Display labels, retaining original typed values for parameterized SQL.
            options = ['(Aucune)'] + list(range(len(values)))
            chosen = st.selectbox(
                f'Valeur pour {display_col}', options,
                format_func=lambda i: '(Aucune)' if i == '(Aucune)' else str(values[i]),
                key=prefix + 'value_' + column
            )
            if st.button('✅ Ajouter ce filtre', key=prefix + 'add_filter', disabled=chosen == '(Aucune)'):
                active_filters[column] = values[chosen]
                st.session_state.pop(prefix + 'editor', None)
                st.session_state.pop(prefix + 'confirm', None)
                st.rerun()

    if active_filters and st.button('❌ Retirer tous les filtres', key=prefix + 'clear'):
        st.session_state[filters_key] = {}
        st.session_state.pop(prefix + 'editor', None)
        st.session_state.pop(prefix + 'confirm', None)
        st.rerun()

    query = sql.SQL('SELECT * FROM my_data')
    params = []
    if active_filters:
        conditions = []
        for column, value in active_filters.items():
            conditions.append(sql.SQL('{} = %s').format(sql.Identifier(column)))
            params.append(value)
        query += sql.SQL(' WHERE ') + sql.SQL(' AND ').join(conditions)
    query += sql.SQL(' ORDER BY id')
    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    df = pd.DataFrame(rows, columns=columns)

    st.write(f'**{len(df)} occurrence(s) trouvée(s)**')
    if df.empty:
        st.info('Aucune occurrence ne correspond à ces filtres.')
        return

    # Keep the database ID as a stable row index, never editable.
    df = df.set_index('id')
    df.index.name = 'id'
    df = df.rename(columns={c: rename_map.get(c, c) for c in df.columns})
    ordered = [c for c in preferred_order if c in df.columns]
    df = df[ordered + [c for c in df.columns if c not in ordered]]
    df.insert(0, '🗑️ Supprimer', False)

    edited = st.data_editor(
        df,
        key=prefix + 'editor',
        hide_index=False,
        use_container_width=True,
        num_rows='fixed',
        disabled=[c for c in df.columns if c != '🗑️ Supprimer'],
        column_config={'🗑️ Supprimer': st.column_config.CheckboxColumn('🗑️ Supprimer', help='Cocher pour sélectionner')},
    )
    ids = [int(i) for i in edited.index[edited['🗑️ Supprimer'] == True].tolist()]
    if not ids:
        st.caption('Cochez au moins une occurrence dans la première colonne pour activer la suppression.')
        return

    st.warning(f'⚠️ {len(ids)} occurrence(s) sélectionnée(s). La suppression est définitive.')
    confirmed = st.checkbox('Je confirme vouloir supprimer ces occurrences et leurs réponses contextuelles.', key=prefix + 'confirm')
    if st.button('🗑️ Supprimer définitivement', type='primary', disabled=not confirmed, key=prefix + 'execute'):
        try:
            # Never use editable table values to identify rows; use original database IDs.
            cursor.execute('DELETE FROM contextual_values WHERE taxon_id = ANY(%s)', (ids,))
            cursor.execute('DELETE FROM my_data WHERE id = ANY(%s)', (ids,))
            count = cursor.rowcount
            conn.commit()
        except Exception as exc:
            conn.rollback()
            st.error(f'Échec de la suppression : {exc}')
        else:
            st.session_state.pop(prefix + 'editor', None)
            st.session_state.pop(prefix + 'confirm', None)
            st.success(f'✅ {count} occurrence(s) supprimée(s).')
            st.rerun()
