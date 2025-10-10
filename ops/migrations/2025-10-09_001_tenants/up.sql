-- Tenants bootstrap (UUID) and 1:1 mapping to core_empresa

-- Ensure required extension for gen_random_uuid
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create tenants table if missing
CREATE TABLE IF NOT EXISTS public.tenants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id integer UNIQUE NOT NULL REFERENCES public.core_empresa(id) ON DELETE CASCADE,
    slug text UNIQUE,
    base_currency text,
    country_code text,
    created_at timestamptz DEFAULT now()
);

-- Backfill tenants from existing empresas (idempotent)
INSERT INTO public.tenants (empresa_id, slug)
SELECT e.id, e.slug
FROM public.core_empresa e
ON CONFLICT (empresa_id) DO NOTHING;

