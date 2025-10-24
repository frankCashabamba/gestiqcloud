-- E-invoicing minimal schema for SRI (EC) and SII (ES)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Per-tenant credentials (use secure storage in prod; this table is for pointers/ids)
CREATE TABLE IF NOT EXISTS public.einvoicing_credentials (
  id serial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  country text NOT NULL CHECK (country IN ('EC','ES')),
  -- For EC (SRI): certificate references
  sri_cert_ref text,
  sri_key_ref text,
  sri_env text,               -- 'staging'|'production'
  -- For ES (SII): endpoints and keys references
  sii_agency text,            -- e.g., 'AEAT'
  sii_cert_ref text,
  sii_key_ref text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, country)
);
CREATE INDEX IF NOT EXISTS ix_einv_creds_tenant ON public.einvoicing_credentials (tenant_id);

-- Ecuador SRI: submissions
CREATE TYPE public.sri_status AS ENUM ('PENDING','SENT','RECEIVED','AUTHORIZED','REJECTED','ERROR');
CREATE TABLE IF NOT EXISTS public.sri_submissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  invoice_id integer NOT NULL,
  status public.sri_status NOT NULL DEFAULT 'PENDING',
  error_code text,
  error_message text,
  receipt_number text,
  authorization_number text,
  payload xml,
  response xml,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sri_submissions_tenant ON public.sri_submissions (tenant_id);
CREATE INDEX IF NOT EXISTS ix_sri_submissions_invoice ON public.sri_submissions (invoice_id);

-- Spain SII: batches
CREATE TYPE public.sii_batch_status AS ENUM ('PENDING','SENT','ACCEPTED','PARTIAL','REJECTED','ERROR');
CREATE TABLE IF NOT EXISTS public.sii_batches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  period text NOT NULL, -- YYYYQn or YYYYMM
  status public.sii_batch_status NOT NULL DEFAULT 'PENDING',
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sii_batches_tenant ON public.sii_batches (tenant_id);

CREATE TYPE public.sii_item_status AS ENUM ('PENDING','SENT','ACCEPTED','REJECTED','ERROR');
CREATE TABLE IF NOT EXISTS public.sii_batch_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  batch_id uuid NOT NULL REFERENCES public.sii_batches(id) ON DELETE CASCADE,
  invoice_id integer NOT NULL,
  status public.sii_item_status NOT NULL DEFAULT 'PENDING',
  error_code text,
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sii_items_tenant ON public.sii_batch_items (tenant_id);
CREATE INDEX IF NOT EXISTS ix_sii_items_batch ON public.sii_batch_items (batch_id);

-- updated_at trigger
CREATE OR REPLACE FUNCTION public._bump_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sri_updated ON public.sri_submissions;
CREATE TRIGGER trg_sri_updated BEFORE UPDATE ON public.sri_submissions FOR EACH ROW EXECUTE PROCEDURE public._bump_updated_at();
DROP TRIGGER IF EXISTS trg_sii_batches_updated ON public.sii_batches;
CREATE TRIGGER trg_sii_batches_updated BEFORE UPDATE ON public.sii_batches FOR EACH ROW EXECUTE PROCEDURE public._bump_updated_at();
DROP TRIGGER IF EXISTS trg_sii_items_updated ON public.sii_batch_items;
CREATE TRIGGER trg_sii_items_updated BEFORE UPDATE ON public.sii_batch_items FOR EACH ROW EXECUTE PROCEDURE public._bump_updated_at();

