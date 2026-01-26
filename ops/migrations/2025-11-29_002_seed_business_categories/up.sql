-- Migración: Insertar datos de ejemplo en business_categories
-- Eliminación de hardcoding: Cargar categorías desde BD
-- Fecha: 29 Noviembre 2025

-- Seed de categorías removido: usar script de seed (ops/scripts/seed_reference_catalogs.py)

-- No-op para mantener consistencia en el pipeline de migraciones
DO $$
BEGIN
    PERFORM 1;
END $$;
