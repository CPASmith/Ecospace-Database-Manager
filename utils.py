import streamlit as st

def select_or_custom(label, options, key_prefix, default=None):
    options = list(set(options))
    options.sort()
    options_with_autre = options + ["(Autre)"]
    options_with_autre = [""] + options_with_autre  # ajoute un choix vide
    index = options_with_autre.index(default) if default in options_with_autre else 0
    choice = st.selectbox(label, options_with_autre, key=f"{key_prefix}_select", index=index)

    if choice == "(Autre)":
        col1, col2 = st.columns([0.1, 0.9])
        with col2:
            custom_input = st.text_input(f"↳ Entrez une nouvelle value pour {label.lower()} :", key=f"{key_prefix}_custom")
            return custom_input if custom_input else None
    return choice


# --- Renommage brut des colonnes (attention à la casse réelle) ---
rename_map = {
        "serie" :"Serie",
        "comment_on_serie" : "Comment on series",
        "stage" : "Stage",
        "comment_on_stage" : "Comment on stage",
        "substage" : "Substage",
        "comment_on_substage" : "Comment on substage",
        "country": "Country",
        "continent": "Continent",
        "lithological_unit" : "Lithological unit",
        "sampling_level/collection" : "Sampling level / Collection",
        "phylum": "Phylum",
        "class": "Class",
        "order": "Order",
        "familly": "Familly",
        "genus": "Genus",
        "comment_on_genus" : "Comment_on_genus",
        "specific_epithet": "Specific epithet",
        "comment_on_species" : "Comment_on_species",
        "species_full_name" : "Species full name",
        "nbr_specimens" : "Number of specimens uncovered",
        "reference" : "Reference",
        "tiering" : "Tiering",
        "feeding" : "Feeding",
        "motility" : "Motility",
        "main_biomineralisation": "Main biomineralisation",
        "size" : "Size",
        "reference_to_ecology" : "Reference on ecology",
        "id" : "Id"
    }
	
	

# --- Réorganisation des colonnes dans l’ordre souhaité ---
preferred_order = [
    "Phylum", "Class", "Order", "Familly", "Genus", "Species full name",
    "Serie", "Stage", "Sub-étage", "Sampling level / Collection", "Lithological unit", "Country", "Continent"
]


def supprimer_dimensions_incompatibles(cursor, taxon_id):
    """Supprime les réponses dont le contexte ne correspond plus à l'occurrence.

    À appeler APRÈS l'UPDATE de my_data, dans la même transaction.
    Une condition NULL dans contexts est un joker ; une valeur NULL dans
    my_data ne satisfait pas une condition non NULL.
    """
    cursor.execute(
        """
        DELETE FROM contextual_values AS cv
        USING contextual_dimensions AS cd, contexts AS c, my_data AS m
        WHERE cv.taxon_id = m.id
          AND cv.contextual_dimensions_id = cd.id
          AND cd.context_id = c.id
          AND m.id = %s
          AND (
              (c.tiering IS NOT NULL AND c.tiering IS DISTINCT FROM m.tiering)
           OR (c.feeding IS NOT NULL AND c.feeding IS DISTINCT FROM m.feeding)
           OR (c.motility IS NOT NULL AND c.motility IS DISTINCT FROM m.motility)
           OR (c.size IS NOT NULL AND c.size IS DISTINCT FROM m.size)
           OR (c.main_biomineralisation IS NOT NULL
               AND c.main_biomineralisation IS DISTINCT FROM m.main_biomineralisation)
          )
        """,
        (int(taxon_id),),
    )
    return cursor.rowcount
