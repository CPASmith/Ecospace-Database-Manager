import streamlit as st
from collections import defaultdict

def generer_schema_ecologique(taxon_id, cursor):
    from collections import defaultdict

    # Récupérer les paramètres écologiques principaux
    cursor.execute("""
        SELECT tiering, motility, feeding, size, main_biomineralisation
        FROM my_data WHERE id = %s
    """, (taxon_id,))
    row = cursor.fetchone()
    if not row:
        st.warning("Taxon introuvable.")
        return

    params = {
        "tiering": row[0],
        "motility": row[1],
        "feeding": row[2],
        "size": row[3],
        "main_biomineralisation": row[4],
    }

    # Récupérer toutes les questions + valeurs associées à ce taxon
    cursor.execute("""
        SELECT dc.id, dc.question, dc.value 
        FROM contextual_values vc 
        JOIN contextual_dimensions dc ON vc.contextual_dimensions_id = dc.id 
        WHERE vc.taxon_id = %s
    """, (taxon_id,))
    contextual_values = cursor.fetchall()

    # Récupérer tous les contextes + dimensions
    cursor.execute("SELECT id, tiering, motility, feeding, size, main_biomineralisation FROM contexts")
    contexts = cursor.fetchall()
    contexts_dict = {
        c[0]: {
            "tiering": c[1], "motility": c[2], "feeding": c[3],
            "size": c[4], "main_biomineralisation": c[5]
        } for c in contexts
    }

    cursor.execute("SELECT id, context_id, question, value FROM contextual_dimensions")
    all_dimensions = cursor.fetchall()

    # Regrouper les dimensions par question
    dimensions_par_question = defaultdict(list)
    for dim_id, context_id, question, value in all_dimensions:
        dimensions_par_question[question].append((dim_id, context_id, value))

    # Regrouper les valeurs renseignées pour ce taxon
    valeurs_du_taxon = defaultdict(list)
    for dim_id, question, val in contextual_values:
        valeurs_du_taxon[question].append((dim_id, val))

    deja_affiches = set()
    markdown = ""

    def afficher_question(question, valeur, profondeur):
        # Styles par niveau
        margin = 20 * profondeur
        margin_top = "12px" if profondeur == 0 else "2px"
        font_size = "0.85em" if profondeur > 0 else "1em"
        color = "#666666" if profondeur > 0 else "#444"
        arrow = "↳" if profondeur > 0 else ""
        
        return f"""
        <div style="
            margin-left: {margin}px;
            margin-top: {margin_top};
            font-size: {font_size};
            color: {color};
            padding: 2px 0;
        ">
            {arrow} <b>{question}</b> = <span style="color:orange;"><b>{valeur}</b></span>
        </div>
        """

    def afficher_parametres_et_dimensions():
        nonlocal markdown

        for param in ["tiering", "motility", "feeding", "size", "main_biomineralisation"]:
            valeur = params.get(param)
            if not valeur:
                continue

            # Paramètre principal
            markdown += afficher_question(param.capitalize(), valeur, profondeur=0)

            # Dimensions dépendantes
            for question, dimensions in dimensions_par_question.items():
                for dim_id, context_id, val_possible in dimensions:
                    ctx = contexts_dict.get(context_id)
                    if not ctx:
                        continue

                    cles_dependantes = [k for k, v in ctx.items() if v]
                    if param not in cles_dependantes:
                        continue

                    if all(params.get(k) == ctx.get(k) for k in cles_dependantes if k in params):
                        valeurs_du_context = valeurs_du_taxon.get(question, [])
                        for dim_id_renseigne, val_renseignee in valeurs_du_context:
                            if val_renseignee == val_possible and (question, val_renseignee) not in deja_affiches:
                                deja_affiches.add((question, val_renseignee))
                                markdown += afficher_question(question, val_renseignee, profondeur=1)

    afficher_parametres_et_dimensions()

    # ➕ Afficher les valeurs restantes non rattachées
    for question, valeurs in valeurs_du_taxon.items():
        for dim_id, val in valeurs:
            if (question, val) not in deja_affiches:
                markdown += f"<br>↪️ <span style='color:gray'><b>{question}</b></span> = <span style='color:orange'><b>{val}</b></span>"

    st.markdown(markdown, unsafe_allow_html=True)




def show_ecologie_schema(conn, cursor):
    st.markdown("## 🌿 Explorer les profils écologiques groupés")

    niveaux = ["phylum", "class", "order", "familly", "genus", "species_full_name"]
    niveau = st.selectbox("🔬 Choisir un niveau taxonomique", niveaux)

    if niveau:
        cursor.execute(f'''
            SELECT DISTINCT "{niveau}" FROM my_data
            WHERE "{niveau}" IS NOT NULL
            ORDER BY "{niveau}" ASC
        ''')
        valeurs = [row[0] for row in cursor.fetchall() if row[0]]
        valeur_choisie = st.selectbox(f"🎯 Choisir une valeur dans {niveau}", valeurs)

        if valeur_choisie:
            # 1. Récupérer tous les taxons correspondant
            cursor.execute(f'''
                SELECT id, species_full_name, genus
                FROM my_data
                WHERE "{niveau}" = %s
                ORDER BY id
            ''', (valeur_choisie,))
            taxons = cursor.fetchall()

            if not taxons:
                st.info("Aucun taxon trouvé pour cette valeur.")
                return

            # 2. Grouper par signature écologique COMPLETE (5 params + dimensions)
            groupes = {}      # clé = signature complète, valeur = liste d'IDs
            noms_par_id = {}  # id -> nom

            for taxon_id, sp_name, genus in taxons:
                # --- 2a) paramètres principaux
                cursor.execute("""
                    SELECT tiering, motility, feeding, size, main_biomineralisation
                    FROM my_data WHERE id = %s
                """, (taxon_id,))
                row = cursor.fetchone()
                if not row:
                    continue
                eco_sig = tuple(row)

                # --- 2b) dimensions (question + valeur) du taxon
                cursor.execute("""
                    SELECT dc.question, vc.value
                    FROM contextual_values vc
                    JOIN contextual_dimensions dc ON vc.contextual_dimensions_id = dc.id
                    WHERE vc.taxon_id = %s
                    ORDER BY dc.question, vc.value
                """, (taxon_id,))
                dims = tuple(cursor.fetchall())  # tuple de (question, value) triés

                signature_complete = (eco_sig, dims)

                groupes.setdefault(signature_complete, []).append(taxon_id)

                nom_affiche = sp_name or genus or f"taxon {taxon_id}"
                noms_par_id[taxon_id] = nom_affiche
    
            # 3. Affichage par groupe
            for i, (signature, id_list) in enumerate(groupes.items(), start=1):
                # Obtenir les noms à partir des vrais id
                liste_noms = sorted({noms_par_id[tid] for tid in id_list})
                noms_texte = ", ".join(liste_noms)

                # Bloc visuel
                st.markdown(f"""
                <div style='
                    background-color: #f0f0f0;
                    border-radius: 6px;
                    padding: 10px; 
                    margin: 10px 0;
                '>
                    <b>Espèces concernées :</b><br>
                    {noms_texte}
                </div>
                """, unsafe_allow_html=True)

                # Appel avec id réel
                generer_schema_ecologique(id_list[0], cursor)
                st.markdown("---")
