-- Alinear columnas de la DB con los modelos ORM.
--
-- Problema: varios modelos heredan de BaseCatalogModel / BaseTransactionalModel
-- que definen columnas (tenant_id, code, is_active, updated_at, etc.) que no
-- existían en las tablas originales. Esto causa:
--   ProgrammingError: column X does not exist
--
-- Esta migración agrega las columnas faltantes sin tocar datos existentes.

BEGIN;

-- ============================================================
-- 1. products: faltaban code, is_active (heredados de BaseCatalogModel)
-- ============================================================
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS code        VARCHAR(50),
    ADD COLUMN IF NOT EXISTS is_active   BOOLEAN NOT NULL DEFAULT true;

-- ============================================================
-- 2. product_categories: faltaban code, is_active
-- ============================================================
ALTER TABLE product_categories
    ADD COLUMN IF NOT EXISTS code        VARCHAR(50),
    ADD COLUMN IF NOT EXISTS is_active   BOOLEAN NOT NULL DEFAULT true;

-- ============================================================
-- 3. business_categories: faltaba tenant_id
--    (config global — el modelo se cambia a BaseCatalogModelWithoutTenant,
--     pero si la tabla ya tiene la columna no pasa nada)
-- ============================================================
-- No se agrega tenant_id: es catálogo global.

-- ============================================================
-- 4. sector_templates: faltaba tenant_id
--    (config global — mismo caso que business_categories)
-- ============================================================
-- No se agrega tenant_id: es catálogo global.

-- ============================================================
-- 5. pos_receipts: faltaba updated_at (BaseTransactionalModel)
-- ============================================================
ALTER TABLE pos_receipts
    ADD COLUMN IF NOT EXISTS updated_at  TIMESTAMP NOT NULL DEFAULT now();

-- ============================================================
-- 6. pos_registers: faltaba updated_at (BaseTransactionalModel)
-- ============================================================
ALTER TABLE pos_registers
    ADD COLUMN IF NOT EXISTS updated_at  TIMESTAMP NOT NULL DEFAULT now();

-- ============================================================
-- 7. warehouses: faltaban created_at, updated_at
-- ============================================================
ALTER TABLE warehouses
    ADD COLUMN IF NOT EXISTS created_at  TIMESTAMP NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at  TIMESTAMP NOT NULL DEFAULT now();

-- ============================================================
-- 8. countries: faltaban description, is_active, created_at, updated_at
-- ============================================================
ALTER TABLE countries
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS is_active   BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS created_at  TIMESTAMP NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at  TIMESTAMP NOT NULL DEFAULT now();

-- ============================================================
-- 9. currencies: faltaban description, is_active, created_at, updated_at
-- ============================================================
ALTER TABLE currencies
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS is_active   BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS created_at  TIMESTAMP NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at  TIMESTAMP NOT NULL DEFAULT now();

-- ============================================================
-- 10. languages: faltaban description, is_active, created_at, updated_at
-- ============================================================
ALTER TABLE languages
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS is_active   BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS created_at  TIMESTAMP NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at  TIMESTAMP NOT NULL DEFAULT now();

-- ============================================================
-- 11. weekdays: faltaban code, description, is_active, created_at, updated_at
-- ============================================================
ALTER TABLE weekdays
    ADD COLUMN IF NOT EXISTS code        VARCHAR(50),
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS is_active   BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS created_at  TIMESTAMP NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at  TIMESTAMP NOT NULL DEFAULT now();

COMMIT;
