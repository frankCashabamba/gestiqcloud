-- Migration: 2026-01-09_000_printer_label_configurations
-- Description: Persist tenant-specific printer label configurations used by the frontend dropdown.

BEGIN;

CREATE TABLE IF NOT EXISTS printer_label_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    printer_port VARCHAR(100) NOT NULL,
    name VARCHAR(60) NOT NULL,
    width_mm DOUBLE PRECISION,
    height_mm DOUBLE PRECISION,
    gap_mm DOUBLE PRECISION,
    copies INTEGER,
    show_price BOOLEAN,
    show_category BOOLEAN,
    header_text VARCHAR(60),
    footer_text VARCHAR(60),
    offset_xmm DOUBLE PRECISION,
    offset_ymm DOUBLE PRECISION,
    barcode_width DOUBLE PRECISION,
    price_alignment VARCHAR(10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_printer_label_configurations_tenant_id
    ON printer_label_configurations (tenant_id);
CREATE INDEX IF NOT EXISTS ix_printer_label_configurations_printer_port
    ON printer_label_configurations (printer_port);

COMMIT;
