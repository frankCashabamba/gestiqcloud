-- Migration: Country catalogs for id types and tax codes
-- Date: 2026-01-16
-- Purpose: Avoid hardcoded id/tax definitions per country

BEGIN;

CREATE TABLE IF NOT EXISTS country_id_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country_code VARCHAR(2) NOT NULL,
    code VARCHAR(20) NOT NULL,
    label VARCHAR(100) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_country_id_types_country_code ON country_id_types(country_code);
CREATE INDEX IF NOT EXISTS ix_country_id_types_code ON country_id_types(code);

CREATE TABLE IF NOT EXISTS country_tax_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country_code VARCHAR(2) NOT NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    rate_default NUMERIC(6,4),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_country_tax_codes_country_code ON country_tax_codes(country_code);
CREATE INDEX IF NOT EXISTS ix_country_tax_codes_code ON country_tax_codes(code);

COMMIT;
