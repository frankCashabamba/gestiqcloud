-- POS: registers, shifts, receipts, items, payments (multi-tenant)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Registers
CREATE TABLE IF NOT EXISTS public.pos_registers (
  id serial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  code varchar NOT NULL,
  name varchar NOT NULL,
  default_warehouse_id integer,
  metadata jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, code)
);
CREATE INDEX IF NOT EXISTS ix_pos_registers_tenant ON public.pos_registers (tenant_id);

-- Shifts
CREATE TABLE IF NOT EXISTS public.pos_shifts (
  id serial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  register_id integer NOT NULL REFERENCES public.pos_registers(id) ON DELETE CASCADE,
  opened_at timestamptz NOT NULL DEFAULT now(),
  closed_at timestamptz,
  opening_cash numeric NOT NULL DEFAULT 0,
  closing_cash numeric,
  status varchar NOT NULL DEFAULT 'open',
  user_id integer,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pos_shifts_tenant ON public.pos_shifts (tenant_id);
CREATE INDEX IF NOT EXISTS ix_pos_shifts_register ON public.pos_shifts (register_id);

-- Receipts
CREATE TABLE IF NOT EXISTS public.pos_receipts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  shift_id integer NOT NULL REFERENCES public.pos_shifts(id) ON DELETE CASCADE,
  status varchar NOT NULL DEFAULT 'draft',
  totals jsonb,
  metadata jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pos_receipts_tenant ON public.pos_receipts (tenant_id);
CREATE INDEX IF NOT EXISTS ix_pos_receipts_shift ON public.pos_receipts (shift_id);

-- Items
CREATE TABLE IF NOT EXISTS public.pos_items (
  id serial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  receipt_id uuid NOT NULL REFERENCES public.pos_receipts(id) ON DELETE CASCADE,
  product_id integer NOT NULL REFERENCES public.products(id),
  qty numeric NOT NULL,
  unit_price numeric NOT NULL DEFAULT 0,
  tax numeric,
  metadata jsonb
);
CREATE INDEX IF NOT EXISTS ix_pos_items_tenant ON public.pos_items (tenant_id);
CREATE INDEX IF NOT EXISTS ix_pos_items_receipt ON public.pos_items (receipt_id);
CREATE INDEX IF NOT EXISTS ix_pos_items_product ON public.pos_items (product_id);

-- Payments
CREATE TABLE IF NOT EXISTS public.pos_payments (
  id serial PRIMARY KEY,
  tenant_id uuid NOT NULL,
  receipt_id uuid NOT NULL REFERENCES public.pos_receipts(id) ON DELETE CASCADE,
  method varchar NOT NULL,
  amount numeric NOT NULL,
  bank_transaction_id integer REFERENCES public.bank_transactions(id),
  metadata jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pos_payments_tenant ON public.pos_payments (tenant_id);
CREATE INDEX IF NOT EXISTS ix_pos_payments_receipt ON public.pos_payments (receipt_id);

