-- Migration: 2026-03-31_001_promotions
-- Tabla de promociones/descuentos comerciales por tenant
BEGIN;

CREATE TABLE IF NOT EXISTS promotions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        VARCHAR(200) NOT NULL,
    description TEXT,
    -- Tipo: 'percentage' | 'fixed' | 'bogo'
    type        VARCHAR(20) NOT NULL DEFAULT 'percentage',
    -- Valor: % o importe fijo según tipo
    value       NUMERIC(12, 4) NOT NULL DEFAULT 0,
    valid_from  DATE,
    valid_to    DATE,
    -- Compra mínima para activar la promoción
    min_purchase NUMERIC(12, 2) DEFAULT 0,
    -- Ámbito: 'all' | 'products'
    applies_to  VARCHAR(20) NOT NULL DEFAULT 'all',
    -- IDs de productos elegibles (solo si applies_to = 'products')
    product_ids UUID[],
    -- Código canjeab le (opcional, case-insensitive)
    promo_code  VARCHAR(100),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    usage_limit INT,
    usage_count INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_promotions_type   CHECK (type IN ('percentage', 'fixed', 'bogo')),
    CONSTRAINT chk_promotions_scope  CHECK (applies_to IN ('all', 'products')),
    CONSTRAINT chk_promotions_value  CHECK (value >= 0),
    CONSTRAINT chk_promotions_pct    CHECK (type != 'percentage' OR value <= 100),
    CONSTRAINT chk_promotions_dates  CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to),
    CONSTRAINT uq_promotions_code    UNIQUE (tenant_id, promo_code)
);

-- Índices
CREATE INDEX IF NOT EXISTS ix_promotions_tenant_id
    ON promotions(tenant_id);

CREATE INDEX IF NOT EXISTS ix_promotions_tenant_active
    ON promotions(tenant_id, is_active);

CREATE INDEX IF NOT EXISTS ix_promotions_valid_range
    ON promotions(tenant_id, valid_from, valid_to);

-- RLS
ALTER TABLE promotions ENABLE ROW LEVEL SECURITY;

CREATE POLICY promotions_tenant_isolation
    ON promotions
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

COMMIT;
