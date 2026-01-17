-- Migration: 2026-01-19_000_add_missing_db_tables
-- Description: Add missing tables found in DB but not in ops/migrations.

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sri_status') THEN
        CREATE TYPE sri_status AS ENUM ('PENDING', 'SENT', 'RECEIVED', 'AUTHORIZED', 'REJECTED', 'ERROR');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sii_batch_status') THEN
        CREATE TYPE sii_batch_status AS ENUM ('PENDING', 'SENT', 'ACCEPTED', 'PARTIAL', 'REJECTED', 'ERROR');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sii_item_status') THEN
        CREATE TYPE sii_item_status AS ENUM ('PENDING', 'SENT', 'ACCEPTED', 'REJECTED', 'ERROR');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS public._migrations (
    id SERIAL NOT NULL,
    name VARCHAR(255) NOT NULL,
    hash VARCHAR(64) NOT NULL,
    applied_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT _migrations_pkey PRIMARY KEY (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS _migrations_name_key ON public._migrations (name);

CREATE TABLE IF NOT EXISTS public.deliveries (
    id SERIAL NOT NULL,
    tenant_id UUID NOT NULL,
    order_id INTEGER NOT NULL,
    status VARCHAR NOT NULL,
    metadata JSON,
    CONSTRAINT deliveries_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_deliveries_tenant_id ON public.deliveries (tenant_id);

CREATE TABLE IF NOT EXISTS public.documents (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    country VARCHAR(5) NOT NULL,
    issued_at TIMESTAMPTZ,
    series VARCHAR(50),
    sequential VARCHAR(50),
    currency VARCHAR(10) NOT NULL,
    template_id VARCHAR(100),
    template_version INTEGER,
    config_version INTEGER,
    config_effective_from VARCHAR(50),
    country_pack_version VARCHAR(20),
    payload JSONB NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT documents_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_documents_doc_type ON public.documents (doc_type);
CREATE INDEX IF NOT EXISTS ix_documents_id ON public.documents (id);
CREATE INDEX IF NOT EXISTS ix_documents_status ON public.documents (status);
CREATE INDEX IF NOT EXISTS ix_documents_tenant_id ON public.documents (tenant_id);

CREATE TABLE IF NOT EXISTS public.einv_credentials (
    id SERIAL NOT NULL,
    tenant_id UUID NOT NULL,
    country VARCHAR(2) NOT NULL,
    sri_cert_ref TEXT,
    sri_key_ref TEXT,
    sri_env VARCHAR(20),
    sii_agency TEXT,
    sii_cert_ref TEXT,
    sii_key_ref TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT einv_credentials_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_einv_credentials_tenant_id ON public.einv_credentials (tenant_id);

CREATE TABLE IF NOT EXISTS public.sector_field_defaults (
    id UUID NOT NULL,
    sector VARCHAR NOT NULL,
    module VARCHAR NOT NULL,
    field VARCHAR NOT NULL,
    visible BOOLEAN NOT NULL,
    required BOOLEAN NOT NULL,
    ord SMALLINT,
    label TEXT,
    help TEXT,
    CONSTRAINT sector_field_defaults_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_sector_field_defaults_module ON public.sector_field_defaults (module);
CREATE INDEX IF NOT EXISTS ix_sector_field_defaults_sector ON public.sector_field_defaults (sector);

CREATE TABLE IF NOT EXISTS public.sector_validation_rules (
    id UUID NOT NULL,
    sector_template_id UUID NOT NULL REFERENCES sector_templates(id),
    context VARCHAR(50) NOT NULL,
    field VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    condition JSON NOT NULL,
    message VARCHAR(500) NOT NULL,
    level VARCHAR(20) NOT NULL,
    enabled BOOLEAN NOT NULL,
    "order" INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT sector_validation_rules_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.sii_batches (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    period VARCHAR(10) NOT NULL,
    status sii_batch_status NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT sii_batches_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_sii_batches_tenant_id ON public.sii_batches (tenant_id);

CREATE TABLE IF NOT EXISTS public.sii_batch_items (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    batch_id UUID NOT NULL REFERENCES sii_batches(id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL,
    status sii_item_status NOT NULL,
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT sii_batch_items_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_sii_batch_items_batch_id ON public.sii_batch_items (batch_id);
CREATE INDEX IF NOT EXISTS ix_sii_batch_items_tenant_id ON public.sii_batch_items (tenant_id);

CREATE TABLE IF NOT EXISTS public.sri_submissions (
    id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    invoice_id UUID NOT NULL,
    status sri_status NOT NULL,
    error_code TEXT,
    error_message TEXT,
    receipt_number TEXT,
    authorization_number TEXT,
    payload TEXT,
    response TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT sri_submissions_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_sri_submissions_invoice_id ON public.sri_submissions (invoice_id);
CREATE INDEX IF NOT EXISTS ix_sri_submissions_tenant_id ON public.sri_submissions (tenant_id);

CREATE TABLE IF NOT EXISTS public.test_items (
    id SERIAL NOT NULL,
    name VARCHAR NOT NULL,
    CONSTRAINT test_items_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_test_items_id ON public.test_items (id);

CREATE TABLE IF NOT EXISTS public.ui_templates (
    id SERIAL NOT NULL,
    slug VARCHAR(100) NOT NULL,
    label VARCHAR(150) NOT NULL,
    description TEXT,
    pro BOOLEAN NOT NULL,
    active BOOLEAN NOT NULL,
    ord INTEGER,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT ui_templates_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_ui_templates_active ON public.ui_templates (active);
CREATE UNIQUE INDEX IF NOT EXISTS ix_ui_templates_slug ON public.ui_templates (slug);

COMMIT;
