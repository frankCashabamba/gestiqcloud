-- SPEC-1: Digitalización de registro de ventas y compras
-- Tablas: daily_inventory, purchase, milk_record, uom, uom_conversion, sale_header, sale_line, import_log

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- UoM (Unidades de Medida) y conversiones
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.uom (
  id SERIAL PRIMARY KEY,
  code VARCHAR(10) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.uom_conversion (
  id SERIAL PRIMARY KEY,
  from_code VARCHAR(10) NOT NULL REFERENCES public.uom(code),
  to_code VARCHAR(10) NOT NULL REFERENCES public.uom(code),
  factor NUMERIC(14, 6) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (from_code, to_code)
);

-- Seeds UoM básicas
INSERT INTO public.uom (code, name, description) VALUES
  ('UN', 'Unidad', 'Unidad discreta'),
  ('KG', 'Kilogramo', 'Masa - kilogramo'),
  ('G', 'Gramo', 'Masa - gramo'),
  ('L', 'Litro', 'Volumen - litro'),
  ('ML', 'Mililitro', 'Volumen - mililitro'),
  ('LB', 'Libra', 'Masa - libra (0.453592 kg)'),
  ('OZ', 'Onza', 'Masa - onza (28.3495 g)'),
  ('DOC', 'Docena', '12 unidades')
ON CONFLICT (code) DO NOTHING;

-- Seeds conversiones
INSERT INTO public.uom_conversion (from_code, to_code, factor) VALUES
  ('G', 'KG', 0.001),
  ('KG', 'G', 1000),
  ('ML', 'L', 0.001),
  ('L', 'ML', 1000),
  ('LB', 'KG', 0.453592),
  ('KG', 'LB', 2.204623),
  ('OZ', 'KG', 0.0283495),
  ('KG', 'OZ', 35.274),
  ('DOC', 'UN', 12),
  ('UN', 'DOC', 0.0833333)
ON CONFLICT (from_code, to_code) DO NOTHING;

-- ============================================================================
-- Daily Inventory (Inventario diario por producto y fecha)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.daily_inventory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES public.tenants(id),
  product_id UUID NOT NULL,
  fecha DATE NOT NULL,
  stock_inicial NUMERIC(14, 3) NOT NULL DEFAULT 0,
  venta_unidades NUMERIC(14, 3) NOT NULL DEFAULT 0,
  stock_final NUMERIC(14, 3) NOT NULL DEFAULT 0,
  ajuste NUMERIC(14, 3) NOT NULL DEFAULT 0,
  precio_unitario_venta NUMERIC(14, 4),
  importe_total NUMERIC(16, 4),
  source_file TEXT,
  source_row INTEGER,
  import_digest BYTEA,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by UUID,
  UNIQUE (tenant_id, product_id, fecha)
);

CREATE INDEX IF NOT EXISTS ix_daily_inventory_tenant ON public.daily_inventory(tenant_id);
CREATE INDEX IF NOT EXISTS ix_daily_inventory_fecha ON public.daily_inventory(tenant_id, fecha);
CREATE INDEX IF NOT EXISTS ix_daily_inventory_product ON public.daily_inventory(product_id);

-- RLS
ALTER TABLE public.daily_inventory ENABLE ROW LEVEL SECURITY;
CREATE POLICY daily_inventory_tenant_isolation ON public.daily_inventory
  USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Purchase (Compras)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.purchase (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES public.tenants(id),
  fecha DATE NOT NULL,
  supplier_name TEXT,
  product_id UUID,
  cantidad NUMERIC(14, 3) NOT NULL,
  costo_unitario NUMERIC(14, 4) NOT NULL,
  total NUMERIC(16, 4),
  notas TEXT,
  source_file TEXT,
  source_row INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by UUID
);

CREATE INDEX IF NOT EXISTS ix_purchase_tenant ON public.purchase(tenant_id);
CREATE INDEX IF NOT EXISTS ix_purchase_fecha ON public.purchase(tenant_id, fecha);
CREATE INDEX IF NOT EXISTS ix_purchase_product ON public.purchase(product_id);

-- RLS
ALTER TABLE public.purchase ENABLE ROW LEVEL SECURITY;
CREATE POLICY purchase_tenant_isolation ON public.purchase
  USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Milk Record (Registro de leche)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.milk_record (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES public.tenants(id),
  fecha DATE NOT NULL,
  litros NUMERIC(14, 3) NOT NULL,
  grasa_pct NUMERIC(5, 2),
  notas TEXT,
  source_file TEXT,
  source_row INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by UUID
);

CREATE INDEX IF NOT EXISTS ix_milk_record_tenant ON public.milk_record(tenant_id);
CREATE INDEX IF NOT EXISTS ix_milk_record_fecha ON public.milk_record(tenant_id, fecha);

-- RLS
ALTER TABLE public.milk_record ENABLE ROW LEVEL SECURITY;
CREATE POLICY milk_record_tenant_isolation ON public.milk_record
  USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Sale Header/Line (documentos de venta simplificados)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.sale_header (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES public.tenants(id),
  fecha DATE NOT NULL,
  customer_id UUID,
  customer_name TEXT DEFAULT 'Consumidor Final',
  total NUMERIC(16, 4) NOT NULL DEFAULT 0,
  total_tax NUMERIC(16, 4) NOT NULL DEFAULT 0,
  payment_method TEXT DEFAULT 'Efectivo',
  sale_uuid UUID UNIQUE,
  pos_receipt_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by UUID
);

CREATE TABLE IF NOT EXISTS public.sale_line (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sale_id UUID NOT NULL REFERENCES public.sale_header(id) ON DELETE CASCADE,
  product_id UUID NOT NULL,
  qty NUMERIC(14, 3) NOT NULL,
  price NUMERIC(14, 4) NOT NULL,
  tax_pct NUMERIC(6, 4) NOT NULL DEFAULT 0,
  total_line NUMERIC(16, 4) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sale_header_tenant ON public.sale_header(tenant_id);
CREATE INDEX IF NOT EXISTS ix_sale_header_fecha ON public.sale_header(tenant_id, fecha);
CREATE INDEX IF NOT EXISTS ix_sale_line_sale ON public.sale_line(sale_id);
CREATE INDEX IF NOT EXISTS ix_sale_line_product ON public.sale_line(product_id);

-- RLS
ALTER TABLE public.sale_header ENABLE ROW LEVEL SECURITY;
CREATE POLICY sale_header_tenant_isolation ON public.sale_header
  USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

ALTER TABLE public.sale_line ENABLE ROW LEVEL SECURITY;
CREATE POLICY sale_line_tenant_isolation ON public.sale_line
  USING (
    EXISTS (
      SELECT 1 FROM public.sale_header
      WHERE sale_header.id = sale_line.sale_id
        AND sale_header.tenant_id::text = current_setting('app.tenant_id', TRUE)
    )
  );

-- ============================================================================
-- Production Order (Órdenes de producción)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.production_order (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES public.tenants(id),
  product_fg_id UUID NOT NULL,
  fecha DATE NOT NULL,
  qty_plan NUMERIC(14, 3) NOT NULL,
  qty_real NUMERIC(14, 3),
  estado VARCHAR(50) NOT NULL DEFAULT 'PLANIFICADA',
  merma_real NUMERIC(14, 3),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by UUID,
  finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_production_order_tenant ON public.production_order(tenant_id);
CREATE INDEX IF NOT EXISTS ix_production_order_fecha ON public.production_order(tenant_id, fecha);
CREATE INDEX IF NOT EXISTS ix_production_order_product ON public.production_order(product_fg_id);
CREATE INDEX IF NOT EXISTS ix_production_order_estado ON public.production_order(estado);

-- RLS
ALTER TABLE public.production_order ENABLE ROW LEVEL SECURITY;
CREATE POLICY production_order_tenant_isolation ON public.production_order
  USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Import Log (trazabilidad de importaciones)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.import_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES public.tenants(id),
  source_file TEXT NOT NULL,
  sheet TEXT NOT NULL,
  source_row INTEGER NOT NULL,
  entity TEXT NOT NULL,
  entity_id UUID NOT NULL,
  digest BYTEA NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, source_file, sheet, source_row)
);

CREATE INDEX IF NOT EXISTS ix_import_log_tenant ON public.import_log(tenant_id);
CREATE INDEX IF NOT EXISTS ix_import_log_entity ON public.import_log(entity, entity_id);

-- RLS
ALTER TABLE public.import_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY import_log_tenant_isolation ON public.import_log
  USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Triggers y funciones auxiliares
-- ============================================================================

-- Auto-calcular ajuste en daily_inventory
CREATE OR REPLACE FUNCTION public.calculate_daily_inventory_ajuste()
RETURNS TRIGGER AS $$
BEGIN
  NEW.ajuste := COALESCE(NEW.stock_inicial, 0) 
              - COALESCE(NEW.venta_unidades, 0) 
              - COALESCE(NEW.stock_final, 0);
  NEW.importe_total := CASE 
    WHEN NEW.precio_unitario_venta IS NULL THEN NULL
    ELSE ROUND(COALESCE(NEW.venta_unidades, 0) * NEW.precio_unitario_venta, 4)
  END;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_daily_inventory_ajuste
  BEFORE INSERT OR UPDATE ON public.daily_inventory
  FOR EACH ROW
  EXECUTE FUNCTION public.calculate_daily_inventory_ajuste();

-- Auto-calcular total en purchase
CREATE OR REPLACE FUNCTION public.calculate_purchase_total()
RETURNS TRIGGER AS $$
BEGIN
  NEW.total := ROUND(NEW.cantidad * NEW.costo_unitario, 4);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_purchase_total
  BEFORE INSERT OR UPDATE ON public.purchase
  FOR EACH ROW
  EXECUTE FUNCTION public.calculate_purchase_total();
