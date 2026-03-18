-- ============================================================
-- 2026-03-17_004_product_variants
-- Agrega soporte de variantes de producto (talla, color, etc.)
-- ============================================================

-- Atributos de variante (define los tipos disponibles por tenant)
CREATE TABLE IF NOT EXISTS product_variant_attributes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    name        VARCHAR(60) NOT NULL,       -- "Talla", "Color", "Material"
    values      JSONB NOT NULL DEFAULT '[]', -- ["S","M","L","XL"] o ["Rojo","Azul"]
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name)
);

-- Variantes concretas de un producto
CREATE TABLE IF NOT EXISTS product_variants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL,
    product_id  UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku         VARCHAR(100),
    attributes  JSONB NOT NULL DEFAULT '{}', -- {"Talla": "M", "Color": "Rojo"}
    price       NUMERIC(14,2),               -- NULL = usa precio del producto padre
    cost        NUMERIC(14,2),
    barcode     VARCHAR(100),
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, product_id, sku)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_product_variants_product
    ON product_variants (tenant_id, product_id);

CREATE INDEX IF NOT EXISTS idx_product_variant_attributes_tenant
    ON product_variant_attributes (tenant_id);

-- RLS
ALTER TABLE product_variant_attributes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pva_tenant ON product_variant_attributes;
CREATE POLICY pva_tenant ON product_variant_attributes
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

ALTER TABLE product_variants ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pv_tenant ON product_variants;
CREATE POLICY pv_tenant ON product_variants
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
