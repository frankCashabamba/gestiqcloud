-- Migration: Production Orders - Órdenes de Producción
-- Fecha: 2025-11-03
-- Descripción: Sistema completo de órdenes de producción con consumo automático de stock

-- 1. Crear tipo ENUM para estados
DO $$ BEGIN
    CREATE TYPE production_order_status AS ENUM (
        'DRAFT',        -- Borrador
        'SCHEDULED',    -- Programado
        'IN_PROGRESS',  -- En proceso
        'COMPLETED',    -- Completado
        'CANCELLED'     -- Cancelado
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- 2. Crear tabla principal: production_orders
CREATE TABLE IF NOT EXISTS production_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,

    -- Numeración
    numero VARCHAR(50) NOT NULL UNIQUE,

    -- Referencias
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE RESTRICT,
    product_id UUID NOT NULL,
    warehouse_id UUID,

    -- Cantidades
    qty_planned NUMERIC(14,3) NOT NULL CHECK (qty_planned > 0),
    qty_produced NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (qty_produced >= 0),
    waste_qty NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (waste_qty >= 0),
    waste_reason TEXT,

    -- Fechas
    scheduled_date TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Estado
    status production_order_status NOT NULL DEFAULT 'DRAFT',
    batch_number VARCHAR(50),

    -- Información adicional
    notes TEXT,
    metadata_json JSONB,

    -- Auditoría
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_completed_dates CHECK (
        (status != 'COMPLETED') OR (started_at IS NOT NULL AND completed_at IS NOT NULL)
    ),
    CONSTRAINT check_production_time CHECK (
        (completed_at IS NULL) OR (started_at IS NULL) OR (completed_at >= started_at)
    )
);

-- 3. Índices para performance
CREATE INDEX IF NOT EXISTS idx_production_orders_tenant ON production_orders(tenant_id);
CREATE INDEX IF NOT EXISTS idx_production_orders_status ON production_orders(status);
CREATE INDEX IF NOT EXISTS idx_production_orders_recipe ON production_orders(recipe_id);
CREATE INDEX IF NOT EXISTS idx_production_orders_product ON production_orders(product_id);
CREATE INDEX IF NOT EXISTS idx_production_orders_batch ON production_orders(batch_number) WHERE batch_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_production_orders_scheduled ON production_orders(scheduled_date) WHERE scheduled_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_production_orders_created ON production_orders(created_at DESC);

-- 4. Row Level Security (RLS)
ALTER TABLE production_orders ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON production_orders;
CREATE POLICY tenant_isolation ON production_orders
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- 5. Crear tabla de líneas: production_order_lines
CREATE TABLE IF NOT EXISTS production_order_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Referencias
    order_id UUID NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,
    ingredient_product_id UUID NOT NULL,
    stock_move_id UUID,

    -- Cantidades
    qty_required NUMERIC(14,3) NOT NULL CHECK (qty_required > 0),
    qty_consumed NUMERIC(14,3) NOT NULL DEFAULT 0 CHECK (qty_consumed >= 0),
    unit VARCHAR(20) NOT NULL DEFAULT 'unit',

    -- Costos
    cost_unit NUMERIC(12,4) NOT NULL DEFAULT 0 CHECK (cost_unit >= 0),
    cost_total NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (cost_total >= 0),

    -- Auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT check_consumed_not_exceeds CHECK (qty_consumed <= qty_required * 1.2)
);

-- 6. Índices para líneas
CREATE INDEX IF NOT EXISTS idx_production_order_lines_order ON production_order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_production_order_lines_ingredient ON production_order_lines(ingredient_product_id);
CREATE INDEX IF NOT EXISTS idx_production_order_lines_stock_move ON production_order_lines(stock_move_id) WHERE stock_move_id IS NOT NULL;

-- 7. RLS para líneas
ALTER TABLE production_order_lines ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON production_order_lines;
CREATE POLICY tenant_isolation ON production_order_lines
    USING (EXISTS (
        SELECT 1 FROM production_orders
        WHERE production_orders.id = production_order_lines.order_id
        AND production_orders.tenant_id::text = current_setting('app.tenant_id', TRUE)
    ));

-- 8. Función para auto-update updated_at
CREATE OR REPLACE FUNCTION update_production_order_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_production_order_updated_at ON production_orders;
CREATE TRIGGER trigger_update_production_order_updated_at
    BEFORE UPDATE ON production_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_production_order_updated_at();

-- 9. Comentarios para documentación
COMMENT ON TABLE production_orders IS 'Órdenes de producción basadas en recetas';
COMMENT ON COLUMN production_orders.numero IS 'Número único de orden (ej: OP-2025-0001)';
COMMENT ON COLUMN production_orders.qty_planned IS 'Cantidad planificada a producir';
COMMENT ON COLUMN production_orders.qty_produced IS 'Cantidad real producida';
COMMENT ON COLUMN production_orders.waste_qty IS 'Mermas y desperdicios';
COMMENT ON COLUMN production_orders.batch_number IS 'Número de lote generado (ej: LOT-202511-0001)';
COMMENT ON COLUMN production_orders.status IS 'Estado: DRAFT, SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED';

COMMENT ON TABLE production_order_lines IS 'Ingredientes consumidos en órdenes de producción';
COMMENT ON COLUMN production_order_lines.qty_required IS 'Cantidad requerida según receta';
COMMENT ON COLUMN production_order_lines.qty_consumed IS 'Cantidad real consumida';
COMMENT ON COLUMN production_order_lines.stock_move_id IS 'Movimiento de stock generado';

-- 10. Datos de ejemplo (opcional - comentar en producción)
-- INSERT INTO production_orders (tenant_id, numero, recipe_id, product_id, qty_planned, status)
-- SELECT
--     '00000000-0000-0000-0000-000000000001'::UUID,
--     'OP-2025-0001',
--     id,
--     product_id,
--     100,
--     'DRAFT'
-- FROM recipes LIMIT 1
-- ON CONFLICT (numero) DO NOTHING;
