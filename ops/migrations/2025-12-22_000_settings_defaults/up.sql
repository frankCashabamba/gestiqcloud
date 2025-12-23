-- Migration: 2025-12-22_000_settings_defaults
-- Description: Store default settings per country in DB

BEGIN;

CREATE TABLE IF NOT EXISTS settings_defaults (
    id SERIAL PRIMARY KEY,
    country VARCHAR(2) NOT NULL,
    name VARCHAR(100) NOT NULL,
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_settings_defaults_country
    ON settings_defaults(country);

CREATE INDEX IF NOT EXISTS idx_settings_defaults_active
    ON settings_defaults(active);

CREATE UNIQUE INDEX IF NOT EXISTS uq_settings_defaults_country_name
    ON settings_defaults(country, name);

CREATE UNIQUE INDEX IF NOT EXISTS uq_settings_defaults_country_default
    ON settings_defaults(country)
    WHERE is_default = TRUE;

COMMIT;
