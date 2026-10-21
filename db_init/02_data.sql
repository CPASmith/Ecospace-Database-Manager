-- Dataset snapshot exported September 2026. All data loaded into a local Docker volume.
COPY public.my_data (serie, comment_on_serie, stage, comment_on_stage, substage, comment_on_substage, country, continent, lithological_unit, sampling_level_collection, collection_name, phylum, class_col, order_col, familly, genus, comment_on_genus, specific_epithet, comment_on_species, species_full_name, nbr_specimens, occurrence_nbr_pbdb, reference, tiering, feeding, motility, size, main_biomineralisation, reference_to_ecology, id) 
FROM '/ecospace-data/my_data.csv' WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8');
COPY public.contexts (id, tiering, feeding, motility, size, main_biomineralisation) FROM '/ecospace-data/contexts.csv' WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8');
COPY public.contextual_dimensions (id, context_id, question, value) FROM '/ecospace-data/contextual_dimensions.csv' WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8');
COPY public.contextual_values (taxon_id, contextual_dimensions_id, value) FROM '/ecospace-data/contextual_values.csv' WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'UTF8');
SELECT setval(pg_get_serial_sequence('public.my_data', 'id'), COALESCE((SELECT MAX(id) FROM public.my_data), 1), (SELECT COUNT(*) > 0 FROM public.my_data));
SELECT setval(pg_get_serial_sequence('public.contexts', 'id'), COALESCE((SELECT MAX(id) FROM public.contexts), 1), (SELECT COUNT(*) > 0 FROM public.contexts));
SELECT setval(pg_get_serial_sequence('public.contextual_dimensions', 'id'), COALESCE((SELECT MAX(id) FROM public.contextual_dimensions), 1), (SELECT COUNT(*) > 0 FROM public.contextual_dimensions));
