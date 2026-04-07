-- Migration: 2026-04-06_000_historical_module
-- Historical data module: import and query sales, purchases, stock
-- without affecting real accounting or inventory.
BEGIN;

-- ─── 1. hist_imports ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS hist_imports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename        VARCHAR(500) NOT NULL,
    file_type       VARCHAR(50),
    file_size_bytes BIGINT,
    import_type     VARCHAR(50) NOT NULL,
    total_rows      INT DEFAULT 0,
    imported_rows   INT DEFAULT 0,
    failed_rows     INT DEFAULT 0,
    status          VARCHAR(30) NOT NULL DEFAULT 'pending',
    error_detail    TEXT,
    imported_by     UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_hist_imports_tenant_id
    ON hist_imports(tenant_id);

ALTER TABLE hist_imports ENABLE ROW LEVEL SECURITY;

CREATE POLICY hist_imports_tenant_isolation
    ON hist_imports
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- ─── 2. hist_masters ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS hist_masters (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entity_type VARCHAR(30) NOT NULL,
    code        VARCHAR(100),
    name        VARCHAR(500) NOT NULL,
    extra       JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_hist_masters_tenant_entity_code UNIQUE (tenant_id, entity_type, code)
);

CREATE INDEX IF NOT EXISTS ix_hist_masters_tenant_id
    ON hist_masters(tenant_id);

ALTER TABLE hist_masters ENABLE ROW LEVEL SECURITY;

CREATE POLICY hist_masters_tenant_isolation
    ON hist_masters
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- ─── 3. hist_sales ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS hist_sales (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    import_id        UUID REFERENCES hist_imports(id) ON DELETE SET NULL,
    fecha            DATE NOT NULL,
    numero           VARCHAR(100),
    cliente_code     VARCHAR(100),
    cliente_nombre   VARCHAR(500),
    producto_code    VARCHAR(100),
    producto_nombre  VARCHAR(500),
    cantidad         NUMERIC(14,4) DEFAULT 0,
    precio_unitario  NUMERIC(14,4) DEFAULT 0,
    subtotal         NUMERIC(14,2) DEFAULT 0,
    impuesto         NUMERIC(14,2) DEFAULT 0,
    total            NUMERIC(14,2) DEFAULT 0,
    moneda           VARCHAR(10) DEFAULT 'USD',
    extra            JSONB DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_hist_sales_tenant_id
    ON hist_sales(tenant_id);

CREATE INDEX IF NOT EXISTS ix_hist_sales_tenant_fecha
    ON hist_sales(tenant_id, fecha);

CREATE INDEX IF NOT EXISTS ix_hist_sales_import_id
    ON hist_sales(import_id);

ALTER TABLE hist_sales ENABLE ROW LEVEL SECURITY;

CREATE POLICY hist_sales_tenant_isolation
    ON hist_sales
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- ─── 4. hist_purchases ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS hist_purchases (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    import_id        UUID REFERENCES hist_imports(id) ON DELETE SET NULL,
    fecha            DATE NOT NULL,
    numero           VARCHAR(100),
    proveedor_code   VARCHAR(100),
    proveedor_nombre VARCHAR(500),
    producto_code    VARCHAR(100),
    producto_nombre  VARCHAR(500),
    cantidad         NUMERIC(14,4) DEFAULT 0,
    precio_unitario  NUMERIC(14,4) DEFAULT 0,
    subtotal         NUMERIC(14,2) DEFAULT 0,
    impuesto         NUMERIC(14,2) DEFAULT 0,
    total            NUMERIC(14,2) DEFAULT 0,
    moneda           VARCHAR(10) DEFAULT 'USD',
    extra            JSONB DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_hist_purchases_tenant_id
    ON hist_purchases(tenant_id);

CREATE INDEX IF NOT EXISTS ix_hist_purchases_tenant_fecha
    ON hist_purchases(tenant_id, fecha);

CREATE INDEX IF NOT EXISTS ix_hist_purchases_import_id
    ON hist_purchases(import_id);

ALTER TABLE hist_purchases ENABLE ROW LEVEL SECURITY;

CREATE POLICY hist_purchases_tenant_isolation
    ON hist_purchases
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- ─── 5. hist_stock ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS hist_stock (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    import_id       UUID REFERENCES hist_imports(id) ON DELETE SET NULL,
    fecha           DATE NOT NULL,
    producto_code   VARCHAR(100),
    producto_nombre VARCHAR(500),
    cantidad        NUMERIC(14,4) DEFAULT 0,
    costo_unitario  NUMERIC(14,4) DEFAULT 0,
    valor_total     NUMERIC(14,2) DEFAULT 0,
    almacen         VARCHAR(200),
    extra           JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_hist_stock_tenant_id
    ON hist_stock(tenant_id);

CREATE INDEX IF NOT EXISTS ix_hist_stock_tenant_fecha
    ON hist_stock(tenant_id, fecha);

CREATE INDEX IF NOT EXISTS ix_hist_stock_import_id
    ON hist_stock(import_id);

ALTER TABLE hist_stock ENABLE ROW LEVEL SECURITY;

CREATE POLICY hist_stock_tenant_isolation
    ON hist_stock
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- ─── 6. hist_daily_sales ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS hist_daily_sales (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    import_id       UUID REFERENCES hist_imports(id) ON DELETE SET NULL,
    fecha           DATE NOT NULL,
    total_ventas    NUMERIC(14,2) DEFAULT 0,
    total_items     INT DEFAULT 0,
    ticket_promedio NUMERIC(14,2) DEFAULT 0,
    extra           JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_hist_daily_sales_tenant_fecha UNIQUE (tenant_id, fecha)
);

CREATE INDEX IF NOT EXISTS ix_hist_daily_sales_tenant_id
    ON hist_daily_sales(tenant_id);

CREATE INDEX IF NOT EXISTS ix_hist_daily_sales_tenant_fecha
    ON hist_daily_sales(tenant_id, fecha);

CREATE INDEX IF NOT EXISTS ix_hist_daily_sales_import_id
    ON hist_daily_sales(import_id);

ALTER TABLE hist_daily_sales ENABLE ROW LEVEL SECURITY;

CREATE POLICY hist_daily_sales_tenant_isolation
    ON hist_daily_sales
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

COMMIT;
