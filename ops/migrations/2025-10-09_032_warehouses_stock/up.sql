-- Warehouses and Stock for multi-tenant inventory

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Warehouses
CREATE TABLE IF NOT EXISTS public.warehouses (
  id serial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  code varchar NOT NULL,
  name varchar NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  metadata jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, code)
);
CREATE INDEX IF NOT EXISTS ix_warehouses_tenant_id ON public.warehouses (tenant_id);

-- Stock items (per warehouse, per product)
CREATE TABLE IF NOT EXISTS public.stock_items (
  id serial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  warehouse_id integer NOT NULL REFERENCES public.warehouses(id) ON DELETE CASCADE,
  product_id integer NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
  qty numeric NOT NULL DEFAULT 0,
  UNIQUE (tenant_id, warehouse_id, product_id)
);
CREATE INDEX IF NOT EXISTS ix_stock_items_tenant_id ON public.stock_items (tenant_id);
CREATE INDEX IF NOT EXISTS ix_stock_items_wh_prod ON public.stock_items (warehouse_id, product_id);

-- Stock movements (reserve/issue/receipt/adjust/release)
CREATE TABLE IF NOT EXISTS public.stock_moves (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  product_id integer NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
  warehouse_id integer NOT NULL REFERENCES public.warehouses(id) ON DELETE CASCADE,
  qty numeric NOT NULL,
  kind varchar NOT NULL CHECK (kind IN ('reserve','issue','receipt','adjust','release')),
  tentative boolean NOT NULL DEFAULT false,
  ref_type varchar,
  ref_id varchar,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stock_moves_tenant_id ON public.stock_moves (tenant_id);
CREATE INDEX IF NOT EXISTS ix_stock_moves_product ON public.stock_moves (product_id);
CREATE INDEX IF NOT EXISTS ix_stock_moves_wh ON public.stock_moves (warehouse_id);

