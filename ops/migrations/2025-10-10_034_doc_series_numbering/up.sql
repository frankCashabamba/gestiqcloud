-- Document series and atomic numbering per tenant

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Series table: one row per (tenant, tipo, año, serie)
CREATE TABLE IF NOT EXISTS public.doc_series (
  id serial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  tipo text NOT NULL,              -- e.g., 'invoice', 'delivery', 'order'
  anio integer NOT NULL,
  serie text NOT NULL,             -- e.g., 'A'
  next_number bigint NOT NULL DEFAULT 1,
  prefix text,
  suffix text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, tipo, anio, serie)
);
CREATE INDEX IF NOT EXISTS ix_doc_series_tenant ON public.doc_series (tenant_id);

-- Trigger to keep updated_at fresh
CREATE OR REPLACE FUNCTION public._bump_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_doc_series_updated_at ON public.doc_series;
CREATE TRIGGER trg_doc_series_updated_at
  BEFORE UPDATE ON public.doc_series
  FOR EACH ROW EXECUTE PROCEDURE public._bump_updated_at();

-- Helper: get current tenant UUID from GUC (returns NULL if unset)
CREATE OR REPLACE FUNCTION public.current_tenant() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT current_setting('app.tenant_id', true)::uuid
$$;

-- Atomic numbering function
-- Returns composed document number like: SERIE-YYYY-000001 (or with prefix/suffix if set)
CREATE OR REPLACE FUNCTION public.assign_next_number(
  p_tenant uuid,
  p_tipo text,
  p_anio int,
  p_serie text
) RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  v_prefix text;
  v_suffix text;
  v_cur bigint;
  v_fmt text;
BEGIN
  IF p_tenant IS NULL THEN
    -- fall back to current_tenant() if not provided
    p_tenant := public.current_tenant();
  END IF;

  IF p_tenant IS NULL THEN
    RAISE EXCEPTION 'assign_next_number: tenant is NULL (set app.tenant_id)';
  END IF;

  -- Ensure a row exists; create if missing
  INSERT INTO public.doc_series(tenant_id, tipo, anio, serie)
  VALUES (p_tenant, p_tipo, p_anio, p_serie)
  ON CONFLICT (tenant_id, tipo, anio, serie) DO NOTHING;

  -- Lock the row and fetch current number and formatting
  SELECT COALESCE(prefix, p_serie || '-' ) AS px,
         suffix,
         next_number
    INTO v_prefix, v_suffix, v_cur
  FROM public.doc_series
  WHERE tenant_id = p_tenant AND tipo = p_tipo AND anio = p_anio AND serie = p_serie
  FOR UPDATE;

  -- Increment counter
  UPDATE public.doc_series
     SET next_number = v_cur + 1
   WHERE tenant_id = p_tenant AND tipo = p_tipo AND anio = p_anio AND serie = p_serie;

  -- Compose number: PREFIX + YYYY + dash + 6-digit padded
  v_fmt := LPAD(v_cur::text, 6, '0');
  RETURN COALESCE(v_prefix, '') || p_anio::text || '-' || v_fmt || COALESCE(v_suffix, '');
END;
$$;

