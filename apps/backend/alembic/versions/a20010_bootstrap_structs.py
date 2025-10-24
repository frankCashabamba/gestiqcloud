"""
Bootstrap core structs (idempotent) for fresh DBs

This revision creates core tables for inventory, sales, POS, templates,
webhooks and e-invoicing using IF NOT EXISTS guards so it is safe on DBs
that already have these objects (no-ops there).

Revision ID: a20010_bootstrap_structs
Revises: a20000_schema_snapshot
Create Date: 2025-10-10
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "a20010_bootstrap_structs"
down_revision = "a20000_schema_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:  # pragma: no cover - DDL heavy
    op.execute(
        """
        -- Helpers
        CREATE OR REPLACE FUNCTION public.current_tenant() RETURNS uuid
        LANGUAGE sql STABLE AS $$
          SELECT current_setting('app.tenant_id', true)::uuid
        $$;

        CREATE OR REPLACE FUNCTION public._bump_updated_at() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          NEW.updated_at := now();
          RETURN NEW;
        END;
        $$;

        -- Inventory
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

        CREATE TABLE IF NOT EXISTS public.stock_items (
          id serial PRIMARY KEY,
          tenant_id uuid NOT NULL,
          warehouse_id integer NOT NULL,
          product_id integer NOT NULL,
          qty numeric NOT NULL DEFAULT 0,
          UNIQUE (tenant_id, warehouse_id, product_id)
        );
        CREATE INDEX IF NOT EXISTS ix_stock_items_tenant_id ON public.stock_items (tenant_id);
        CREATE INDEX IF NOT EXISTS ix_stock_items_wh_prod ON public.stock_items (warehouse_id, product_id);

        CREATE TABLE IF NOT EXISTS public.stock_moves (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id uuid NOT NULL,
          product_id integer NOT NULL,
          warehouse_id integer NOT NULL,
          qty numeric NOT NULL,
          kind varchar NOT NULL,
          tentative boolean NOT NULL DEFAULT false,
          posted boolean NOT NULL DEFAULT false,
          ref_type varchar,
          ref_id varchar,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_stock_moves_tenant_id ON public.stock_moves (tenant_id);
        CREATE INDEX IF NOT EXISTS ix_stock_moves_product ON public.stock_moves (product_id);
        CREATE INDEX IF NOT EXISTS ix_stock_moves_wh ON public.stock_moves (warehouse_id);
        CREATE INDEX IF NOT EXISTS ix_stock_moves_posted ON public.stock_moves (posted);

        -- Sales
        CREATE TABLE IF NOT EXISTS public.sales_orders (
          id serial PRIMARY KEY,
          tenant_id uuid NOT NULL,
          customer_id integer,
          status varchar NOT NULL DEFAULT 'draft',
          currency varchar,
          totals jsonb,
          metadata jsonb,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_sales_orders_tenant_id ON public.sales_orders (tenant_id);

        CREATE TABLE IF NOT EXISTS public.sales_order_items (
          id serial PRIMARY KEY,
          tenant_id uuid NOT NULL,
          order_id integer NOT NULL,
          product_id integer NOT NULL,
          qty numeric NOT NULL,
          unit_price numeric NOT NULL DEFAULT 0,
          tax jsonb,
          metadata jsonb
        );
        CREATE INDEX IF NOT EXISTS ix_sales_order_items_tenant_id ON public.sales_order_items (tenant_id);
        CREATE INDEX IF NOT EXISTS ix_sales_order_items_order ON public.sales_order_items (order_id);

        CREATE TABLE IF NOT EXISTS public.deliveries (
          id serial PRIMARY KEY,
          tenant_id uuid NOT NULL,
          order_id integer NOT NULL,
          status varchar NOT NULL DEFAULT 'pending',
          metadata jsonb,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_deliveries_tenant_id ON public.deliveries (tenant_id);
        CREATE INDEX IF NOT EXISTS ix_deliveries_order ON public.deliveries (order_id);

        -- Doc series + numbering
        CREATE TABLE IF NOT EXISTS public.doc_series (
          id serial PRIMARY KEY,
          tenant_id uuid NOT NULL,
          tipo text NOT NULL,
          anio integer NOT NULL,
          serie text NOT NULL,
          next_number bigint NOT NULL DEFAULT 1,
          prefix text,
          suffix text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, tipo, anio, serie)
        );
        CREATE INDEX IF NOT EXISTS ix_doc_series_tenant ON public.doc_series (tenant_id);
        DROP TRIGGER IF EXISTS trg_doc_series_updated_at ON public.doc_series;
        CREATE TRIGGER trg_doc_series_updated_at
          BEFORE UPDATE ON public.doc_series
          FOR EACH ROW EXECUTE PROCEDURE public._bump_updated_at();

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
            p_tenant := public.current_tenant();
          END IF;
          IF p_tenant IS NULL THEN
            RAISE EXCEPTION 'assign_next_number: tenant is NULL (set app.tenant_id)';
          END IF;
          INSERT INTO public.doc_series(tenant_id, tipo, anio, serie)
          VALUES (p_tenant, p_tipo, p_anio, p_serie)
          ON CONFLICT (tenant_id, tipo, anio, serie) DO NOTHING;
          SELECT COALESCE(prefix, p_serie || '-' ), suffix, next_number
            INTO v_prefix, v_suffix, v_cur
          FROM public.doc_series
          WHERE tenant_id = p_tenant AND tipo = p_tipo AND anio = p_anio AND serie = p_serie
          FOR UPDATE;
          UPDATE public.doc_series SET next_number = v_cur + 1
            WHERE tenant_id = p_tenant AND tipo = p_tipo AND anio = p_anio AND serie = p_serie;
          v_fmt := LPAD(v_cur::text, 6, '0');
          RETURN COALESCE(v_prefix, '') || p_anio::text || '-' || v_fmt || COALESCE(v_suffix, '');
        END;
        $$;

        -- POS
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

        CREATE TABLE IF NOT EXISTS public.pos_shifts (
          id serial PRIMARY KEY,
          tenant_id uuid NOT NULL,
          register_id integer NOT NULL,
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

        CREATE TABLE IF NOT EXISTS public.pos_receipts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id uuid NOT NULL,
          shift_id integer NOT NULL,
          status varchar NOT NULL DEFAULT 'draft',
          totals jsonb,
          metadata jsonb,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_pos_receipts_tenant ON public.pos_receipts (tenant_id);
        CREATE INDEX IF NOT EXISTS ix_pos_receipts_shift ON public.pos_receipts (shift_id);

        CREATE TABLE IF NOT EXISTS public.pos_items (
          id serial PRIMARY KEY,
          tenant_id uuid NOT NULL,
          receipt_id uuid NOT NULL,
          product_id integer NOT NULL,
          qty numeric NOT NULL,
          unit_price numeric NOT NULL DEFAULT 0,
          tax numeric,
          metadata jsonb
        );
        CREATE INDEX IF NOT EXISTS ix_pos_items_tenant ON public.pos_items (tenant_id);
        CREATE INDEX IF NOT EXISTS ix_pos_items_receipt ON public.pos_items (receipt_id);
        CREATE INDEX IF NOT EXISTS ix_pos_items_product ON public.pos_items (product_id);

        CREATE TABLE IF NOT EXISTS public.pos_payments (
          id serial PRIMARY KEY,
          tenant_id uuid NOT NULL,
          receipt_id uuid NOT NULL,
          method varchar NOT NULL,
          amount numeric NOT NULL,
          bank_transaction_id integer,
          metadata jsonb,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_pos_payments_tenant ON public.pos_payments (tenant_id);
        CREATE INDEX IF NOT EXISTS ix_pos_payments_receipt ON public.pos_payments (receipt_id);

        -- Templates
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
          limits jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id)
        );

        -- Webhooks
        CREATE TABLE IF NOT EXISTS public.webhook_subscriptions (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id uuid NOT NULL,
          event text NOT NULL,
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
          status text NOT NULL DEFAULT 'PENDING',
          attempts int NOT NULL DEFAULT 0,
          last_error text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_webhook_deliv_tenant ON public.webhook_deliveries (tenant_id);
        CREATE INDEX IF NOT EXISTS ix_webhook_deliv_status ON public.webhook_deliveries (status);
        DROP TRIGGER IF EXISTS trg_webhook_deliveries_updated ON public.webhook_deliveries;
        CREATE TRIGGER trg_webhook_deliveries_updated BEFORE UPDATE ON public.webhook_deliveries FOR EACH ROW EXECUTE PROCEDURE public._bump_updated_at();

        -- E-invoicing
        CREATE TABLE IF NOT EXISTS public.einvoicing_credentials (
          id serial PRIMARY KEY,
          tenant_id uuid NOT NULL,
          country text NOT NULL,
          sri_cert_ref text,
          sri_key_ref text,
          sri_env text,
          sii_agency text,
          sii_cert_ref text,
          sii_key_ref text,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (tenant_id, country)
        );
        CREATE INDEX IF NOT EXISTS ix_einv_creds_tenant ON public.einvoicing_credentials (tenant_id);
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='sri_status') THEN
            CREATE TYPE public.sri_status AS ENUM ('PENDING','SENT','RECEIVED','AUTHORIZED','REJECTED','ERROR');
          END IF;
        END $$;
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
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='sii_batch_status') THEN
            CREATE TYPE public.sii_batch_status AS ENUM ('PENDING','SENT','ACCEPTED','PARTIAL','REJECTED','ERROR');
          END IF;
        END $$;
        CREATE TABLE IF NOT EXISTS public.sii_batches (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id uuid NOT NULL,
          period text NOT NULL,
          status public.sii_batch_status NOT NULL DEFAULT 'PENDING',
          error_message text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_sii_batches_tenant ON public.sii_batches (tenant_id);
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='sii_item_status') THEN
            CREATE TYPE public.sii_item_status AS ENUM ('PENDING','SENT','ACCEPTED','REJECTED','ERROR');
          END IF;
        END $$;
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
        """
    )


def downgrade() -> None:  # pragma: no cover - destructive down not supported
    # No automatic teardown; managed across versions forward only.
    pass

