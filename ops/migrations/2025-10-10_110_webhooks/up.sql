-- Tenant webhooks: subscriptions and deliveries

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.webhook_subscriptions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  event text NOT NULL,         -- e.g., invoice.posted
  url text NOT NULL,
  secret text,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_webhook_subs_tenant ON public.webhook_subscriptions (tenant_id);
CREATE INDEX IF NOT EXISTS ix_webhook_subs_event ON public.webhook_subscriptions (event);

CREATE TABLE IF NOT EXISTS public.webhook_deliveries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  event text NOT NULL,
  payload jsonb NOT NULL,
  target_url text NOT NULL,
  status text NOT NULL DEFAULT 'PENDING',  -- PENDING|SENT|FAILED
  attempts int NOT NULL DEFAULT 0,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_webhook_deliv_tenant ON public.webhook_deliveries (tenant_id);
CREATE INDEX IF NOT EXISTS ix_webhook_deliv_status ON public.webhook_deliveries (status);

CREATE OR REPLACE FUNCTION public._bump_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_webhook_deliveries_updated ON public.webhook_deliveries;
CREATE TRIGGER trg_webhook_deliveries_updated BEFORE UPDATE ON public.webhook_deliveries FOR EACH ROW EXECUTE PROCEDURE public._bump_updated_at();

