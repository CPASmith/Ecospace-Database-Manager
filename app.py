import streamlit as st
from db import get_connection
from ui.explore_taxa import show_explorer
from ui.add_taxa import show_add_form
from ui.delete_taxa import show_deletion_interface
from ui.ecologie_schema import show_ecologie_schema
from ui.ecological_hierarchy import show_full_ecological_hierarchy

st.set_page_config(layout="wide")
st.title("🌿 Explorateur d'écospaces")

# Initialisation des états
if "show_add_taxa" not in st.session_state:
    st.session_state["show_add_taxa"] = False
if "show_my_data_table" not in st.session_state:
    st.session_state["show_my_data_table"] = False
if "show_deletion_interface" not in st.session_state:
    st.session_state["show_deletion_interface"] = False
if "show_full_hierarchy" not in st.session_state:
    st.session_state["show_full_hierarchy"] = False
if "show_ecologie_schema" not in st.session_state:
    st.session_state["show_ecologie_schema"] = False
    st.session_state["show_full_hierarchy"] = False

# Boutons de navigation
if st.button("📄 Afficher mes données"):
    st.session_state["show_my_data_table"] = True
    st.session_state["show_add_taxa"] = False
    st.session_state["show_deletion_interface"] = False
    st.session_state["show_ecologie_schema"] = False
    st.session_state["show_full_hierarchy"] = False

if st.button("➕ Ajouter une donné"):
    st.session_state["show_my_data_table"] = False
    st.session_state["show_add_taxa"] = True
    st.session_state["show_deletion_interface"] = False
    st.session_state["show_ecologie_schema"] = False
    st.session_state["show_full_hierarchy"] = False

if st.button("🗑️ Supprimer des données"):
    st.session_state["show_my_data_table"] = False
    st.session_state["show_add_taxa"] = False
    st.session_state["show_deletion_interface"] = True
    st.session_state["show_ecologie_schema"] = False
    st.session_state["show_full_hierarchy"] = False
    
if st.button("🔎 Explorer un profil écologique"):
    st.session_state["show_my_data_table"] = False
    st.session_state["show_add_taxa"] = False
    st.session_state["show_deletion_interface"] = False
    st.session_state["show_ecologie_schema"] = True

if st.button("🧬 Visualiser la hiérarchie écologique complète"):
    st.session_state["show_my_data_table"] = False
    st.session_state["show_add_taxa"] = False
    st.session_state["show_deletion_interface"] = False
    st.session_state["show_ecologie_schema"] = False
    st.session_state["show_full_hierarchy"] = True

# Connexion à la base
conn, cursor = get_connection()

# Affichage des sections
if st.session_state["show_my_data_table"]:
    show_explorer(conn, cursor)

elif st.session_state["show_add_taxa"]:
    show_add_form(conn, cursor)

elif st.session_state["show_deletion_interface"]:
    show_deletion_interface(conn, cursor)
    
elif st.session_state["show_ecologie_schema"]:
    show_ecologie_schema(conn, cursor)
    
elif st.session_state["show_full_hierarchy"]:
    show_full_ecological_hierarchy(conn, cursor)

cursor.close()
conn.close()
