BEGIN;

DROP TABLE IF EXISTS imp_config;

-- Nota: los datos en sector_field_defaults (sector='_system', module LIKE 'importador.%')
-- NO fueron eliminados en el up.sql, por lo que siguen disponibles si se necesita
-- volver a la versión anterior del código.

COMMIT;
