-- Sales orders, items and deliveries (multi-tenant)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Orders
CREATE TABLE IF NOT EXISTS public.sales_orders (
  id serial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  customer_id integer,
  status varchar NOT NULL DEFAULT 'draft', -- draft|confirmed|delivered|cancelled
  currency varchar,
  totals jsonb,
  metadata jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sales_orders_tenant_id ON public.sales_orders (tenant_id);

-- Items
CREATE TABLE IF NOT EXISTS public.sales_order_items (
  id serial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  order_id integer NOT NULL REFERENCES public.sales_orders(id) ON DELETE CASCADE,
  product_id integer NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
  qty numeric NOT NULL,
  unit_price numeric NOT NULL DEFAULT 0,
  tax jsonb,
  metadata jsonb
);
CREATE INDEX IF NOT EXISTS ix_sales_order_items_tenant_id ON public.sales_order_items (tenant_id);
CREATE INDEX IF NOT EXISTS ix_sales_order_items_order ON public.sales_order_items (order_id);

-- Deliveries
CREATE TABLE IF NOT EXISTS public.deliveries (
  id serial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  order_id integer NOT NULL REFERENCES public.sales_orders(id) ON DELETE CASCADE,
  status varchar NOT NULL DEFAULT 'pending', -- pending|done|cancelled
  metadata jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_deliveries_tenant_id ON public.deliveries (tenant_id);
CREATE INDEX IF NOT EXISTS ix_deliveries_order ON public.deliveries (order_id);

