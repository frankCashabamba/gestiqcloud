-- Migrar tablas de catálogo global (languages, currencies, countries, weekdays,
-- business_hours) de INTEGER PK a UUID PK.
--
-- También se corrige company_settings.language_id y currency_id a UUID.
-- Entorno local/dev — se recrean las tablas con datos seed limpios.

BEGIN;

-- ============================================================
-- 1. Limpiar FKs en company_settings antes de DROP
-- ============================================================
ALTER TABLE company_settings
    DROP COLUMN IF EXISTS language_id,
    DROP COLUMN IF EXISTS currency_id;

-- ============================================================
-- 2. Recrear business_hours (depende de weekdays, va primero el DROP)
-- ============================================================
DROP TABLE IF EXISTS business_hours CASCADE;

-- ============================================================
-- 3. Recrear weekdays
-- ============================================================
DROP TABLE IF EXISTS weekdays CASCADE;
CREATE TABLE weekdays (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(50),
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    is_active   BOOLEAN      NOT NULL DEFAULT true,
    created_at  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT now(),
    key         VARCHAR(20)  UNIQUE,
    "order"     INTEGER      NOT NULL
);

INSERT INTO weekdays (id, name, key, "order") VALUES
    (gen_random_uuid(), 'Lunes',     'monday',    1),
    (gen_random_uuid(), 'Martes',    'tuesday',   2),
    (gen_random_uuid(), 'Miércoles', 'wednesday', 3),
    (gen_random_uuid(), 'Jueves',    'thursday',  4),
    (gen_random_uuid(), 'Viernes',   'friday',    5),
    (gen_random_uuid(), 'Sábado',    'saturday',  6),
    (gen_random_uuid(), 'Domingo',   'sunday',    7);

-- ============================================================
-- 4. Recrear business_hours con UUID
-- ============================================================
CREATE TABLE business_hours (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    weekday_id  UUID         NOT NULL REFERENCES weekdays(id),
    start_time  VARCHAR(5)   NOT NULL,
    end_time    VARCHAR(5)   NOT NULL
);

-- ============================================================
-- 5. Recrear languages
-- ============================================================
DROP TABLE IF EXISTS languages CASCADE;
CREATE TABLE languages (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(10)  UNIQUE NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    is_active   BOOLEAN      NOT NULL DEFAULT true,
    created_at  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT now()
);

INSERT INTO languages (id, code, name) VALUES
    (gen_random_uuid(), 'es',    'Español'),
    (gen_random_uuid(), 'en',    'English'),
    (gen_random_uuid(), 'fr',    'Français'),
    (gen_random_uuid(), 'pt',    'Português'),
    (gen_random_uuid(), 'de',    'Deutsch'),
    (gen_random_uuid(), 'it',    'Italiano'),
    (gen_random_uuid(), 'ca',    'Català'),
    (gen_random_uuid(), 'eu',    'Euskara'),
    (gen_random_uuid(), 'gl',    'Galego'),
    (gen_random_uuid(), 'es_EC', 'Español (Ecuador)'),
    (gen_random_uuid(), 'es_ES', 'Español (España)'),
    (gen_random_uuid(), 'es_MX', 'Español (México)'),
    (gen_random_uuid(), 'es_CO', 'Español (Colombia)'),
    (gen_random_uuid(), 'es_AR', 'Español (Argentina)'),
    (gen_random_uuid(), 'es_PE', 'Español (Perú)'),
    (gen_random_uuid(), 'es_CL', 'Español (Chile)'),
    (gen_random_uuid(), 'en_US', 'English (US)'),
    (gen_random_uuid(), 'en_GB', 'English (UK)'),
    (gen_random_uuid(), 'pt_BR', 'Português (Brasil)');

-- ============================================================
-- 6. Recrear currencies
-- ============================================================
DROP TABLE IF EXISTS currencies CASCADE;
CREATE TABLE currencies (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(10)  UNIQUE NOT NULL,
    name        VARCHAR(100) NOT NULL,
    symbol      VARCHAR(5)   NOT NULL,
    description TEXT,
    is_active   BOOLEAN      NOT NULL DEFAULT true,
    created_at  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT now()
);

INSERT INTO currencies (id, code, name, symbol) VALUES
    (gen_random_uuid(), 'USD', 'Dólar estadounidense', '$'),
    (gen_random_uuid(), 'EUR', 'Euro',                 '€'),
    (gen_random_uuid(), 'MXN', 'Peso mexicano',        '$'),
    (gen_random_uuid(), 'COP', 'Peso colombiano',      '$'),
    (gen_random_uuid(), 'ARS', 'Peso argentino',       '$'),
    (gen_random_uuid(), 'PEN', 'Sol peruano',          'S/'),
    (gen_random_uuid(), 'CLP', 'Peso chileno',         '$'),
    (gen_random_uuid(), 'BRL', 'Real brasileño',       'R$'),
    (gen_random_uuid(), 'GBP', 'Libra esterlina',      '£');

-- ============================================================
-- 7. Recrear countries
-- ============================================================
DROP TABLE IF EXISTS countries CASCADE;
CREATE TABLE countries (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(2)   UNIQUE NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    is_active   BOOLEAN      NOT NULL DEFAULT true,
    created_at  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT now()
);

INSERT INTO countries (id, code, name) VALUES
    (gen_random_uuid(), 'EC', 'Ecuador'),
    (gen_random_uuid(), 'ES', 'España'),
    (gen_random_uuid(), 'MX', 'México'),
    (gen_random_uuid(), 'CO', 'Colombia'),
    (gen_random_uuid(), 'AR', 'Argentina'),
    (gen_random_uuid(), 'PE', 'Perú'),
    (gen_random_uuid(), 'CL', 'Chile'),
    (gen_random_uuid(), 'BR', 'Brasil'),
    (gen_random_uuid(), 'US', 'Estados Unidos'),
    (gen_random_uuid(), 'FR', 'Francia'),
    (gen_random_uuid(), 'DE', 'Alemania'),
    (gen_random_uuid(), 'IT', 'Italia'),
    (gen_random_uuid(), 'PT', 'Portugal'),
    (gen_random_uuid(), 'GB', 'Reino Unido');

-- ============================================================
-- 8. Re-agregar language_id y currency_id como UUID en company_settings
-- ============================================================
ALTER TABLE company_settings
    ADD COLUMN IF NOT EXISTS language_id UUID REFERENCES languages(id),
    ADD COLUMN IF NOT EXISTS currency_id UUID REFERENCES currencies(id);

COMMIT;
