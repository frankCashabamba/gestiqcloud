-- 101_einv_settings.sql
-- Ajustes de facturación electrónica por tenant y país (profesional, extensible y con RLS)

BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- País por configuración (ampliable)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'einv_country') THEN
    CREATE TYPE einv_country AS ENUM ('ES','EC');
  END IF;
END $$;

-- Fuente/destino (ampliable)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'einv_source') THEN
    CREATE TYPE einv_source AS ENUM ('SRI','SII');
  END IF;
END $$;

-- Ajustes por tenant/país. Referencias a secretos en lugar de almacenar certificados directamente.
CREATE TABLE IF NOT EXISTS tenant_einv_settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  country einv_country NOT NULL,

  -- Ecuador (SRI)
  sri_enabled boolean NOT NULL DEFAULT false,
  sri_env text CHECK (sri_env IN ('test','prod')),
  sri_ruc text,
  sri_estab text,              -- establecimiento
  sri_punto_emision text,      -- punto de emisión
  sri_cert_ref text,           -- referencia al secreto del .p12
  sri_software_id text,

  -- España (SII)
  sii_enabled boolean NOT NULL DEFAULT false,
  sii_nif text,
  sii_cert_ref text,           -- referencia al secreto del certificado/clave
  sii_send_mode text NOT NULL DEFAULT 'batch' CHECK (sii_send_mode IN ('immediate','batch')),

  -- Metadatos
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),

  UNIQUE (tenant_id, country)
);

-- Trigger de updated_at
CREATE OR REPLACE FUNCTION trg_set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tg_tenant_einv_settings_updated ON tenant_einv_settings;
CREATE TRIGGER tg_tenant_einv_settings_updated
BEFORE UPDATE ON tenant_einv_settings
FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- RLS
ALTER TABLE tenant_einv_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_einv_settings FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS rls_tenant ON tenant_einv_settings;
CREATE POLICY rls_tenant ON tenant_einv_settings
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Helpers para lectura segura por request/tenant
CREATE OR REPLACE FUNCTION current_tenant_einv_settings(p_country einv_country)
RETURNS tenant_einv_settings AS $$
  SELECT *
  FROM tenant_einv_settings
  WHERE tenant_id = current_setting('app.tenant_id', true)::uuid
    AND country = p_country
  LIMIT 1;
$$ LANGUAGE sql STABLE;

COMMIT;
