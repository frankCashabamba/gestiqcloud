-- Historial diario de producción y ventas
-- Importado desde hojas tipo REGISTRO (PRODUCTO, CANTIDAD, PRECIO, VENTA DIARIA)

CREATE TABLE IF NOT EXISTS daily_production_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    log_date        DATE NOT NULL,

    -- Producto (vinculado si existe en catálogo)
    product_name    TEXT NOT NULL,
    recipe_id       UUID REFERENCES recipes(id) ON DELETE SET NULL,
    product_id      UUID REFERENCES products(id) ON DELETE SET NULL,

    -- Cantidades del día
    qty_produced    NUMERIC(12, 4) NOT NULL DEFAULT 0,
    unit_price      NUMERIC(12, 4) NOT NULL DEFAULT 0,
    qty_sold        NUMERIC(12, 4) NOT NULL DEFAULT 0,

    -- Calculados
    qty_leftover    NUMERIC(12, 4) GENERATED ALWAYS AS (qty_produced - qty_sold) STORED,
    revenue         NUMERIC(12, 4) GENERATED ALWAYS AS (qty_sold * unit_price) STORED,

    -- Origen
    source_document_id UUID REFERENCES imp_documento(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_daily_prod_logs_tenant_date
    ON daily_production_logs (tenant_id, log_date DESC);

CREATE INDEX IF NOT EXISTS idx_daily_prod_logs_recipe
    ON daily_production_logs (recipe_id)
    WHERE recipe_id IS NOT NULL;
