-- Crear tablas de referencia en inglés
-- Migration: 2025-11-01_170_reference_tables

BEGIN;

-- Currencies
CREATE TABLE IF NOT EXISTS currencies (
    id SERIAL PRIMARY KEY,
    code VARCHAR(3) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10),
    active BOOLEAN DEFAULT true
);

INSERT INTO currencies (code, name, symbol, active) VALUES
('USD', 'US Dollar', '$', true),
('EUR', 'Euro', '€', true),
('GBP', 'British Pound', '£', true)
ON CONFLICT (code) DO NOTHING;

-- Countries
CREATE TABLE IF NOT EXISTS countries (
    id SERIAL PRIMARY KEY,
    code VARCHAR(2) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    active BOOLEAN DEFAULT true
);

INSERT INTO countries (code, name, active) VALUES
('US', 'United States', true),
('ES', 'Spain', true),
('EC', 'Ecuador', true),
('GB', 'United Kingdom', true),
('MX', 'Mexico', true)
ON CONFLICT (code) DO NOTHING;

-- Locales
CREATE TABLE IF NOT EXISTS locales (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    active BOOLEAN DEFAULT true
);

INSERT INTO locales (code, name, active) VALUES
('en_US', 'English (US)', true),
('es_ES', 'Spanish (Spain)', true),
('es_EC', 'Spanish (Ecuador)', true)
ON CONFLICT (code) DO NOTHING;

-- Timezones
CREATE TABLE IF NOT EXISTS timezones (
    name VARCHAR(50) PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    offset_minutes INTEGER NOT NULL,
    active BOOLEAN DEFAULT true
);

INSERT INTO timezones (name, display_name, offset_minutes, active) VALUES
('UTC', 'UTC', 0, true),
('America/New_York', 'Eastern Time (US)', -300, true),
('Europe/Madrid', 'Central European Time', 60, true),
('America/Guayaquil', 'Ecuador Time', -300, true)
ON CONFLICT (name) DO NOTHING;

-- Tenant field configuration
CREATE TABLE IF NOT EXISTS tenant_field_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    module VARCHAR(50) NOT NULL,
    field VARCHAR(100) NOT NULL,
    visible BOOLEAN DEFAULT true,
    required BOOLEAN DEFAULT false,
    ord INTEGER,
    label VARCHAR(200),
    help TEXT,
    UNIQUE(tenant_id, module, field)
);

CREATE INDEX IF NOT EXISTS idx_tenant_field_configs_tenant_module ON tenant_field_configs(tenant_id, module);

COMMIT;
