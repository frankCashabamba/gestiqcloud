-- Templates and overlays for UI configuration per tenant

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.template_packages (
  id serial PRIMARY KEY,
  template_key text NOT NULL,
  version integer NOT NULL,
  config jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (template_key, version)
);

CREATE TABLE IF NOT EXISTS public.tenant_templates (
  tenant_id uuid NOT NULL,
  template_key text NOT NULL,
  version integer NOT NULL,
  active boolean NOT NULL DEFAULT true,
  assigned_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, template_key)
);

CREATE TABLE IF NOT EXISTS public.template_overlays (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  name text NOT NULL,
  config jsonb NOT NULL,
  active boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_template_overlays_tenant ON public.template_overlays (tenant_id);

CREATE TABLE IF NOT EXISTS public.template_policies (
  id serial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  limits jsonb NOT NULL,     -- e.g., {"max_fields":15, "max_bytes":8192, "max_depth":2}
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id)
);

-- Seeds: minimal Bazar v1 and Bakery v1
INSERT INTO public.template_packages (template_key, version, config) VALUES
  ('bazar', 1, '{"modules":{"ventas":true,"inventario":true},"ui":{"products":{"columns":["sku","name","price"],"filters":["sku","name"]}}}'),
  ('bakery', 1, '{"modules":{"ventas":true,"inventario":true},"ui":{"products":{"columns":["sku","name","price","grams"],"filters":["sku","name"]}}}')
ON CONFLICT (template_key, version) DO NOTHING;

