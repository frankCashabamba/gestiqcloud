-- ============================================================================
-- Migration: 2025-11-03_202_finance_caja
-- Descripción: Sistema completo de gestión de caja con movimientos y cierres diarios
-- Autor: GestiQCloud Team
-- Fecha: 2025-11-03
-- ============================================================================

-- Crear tipos ENUM para caja
CREATE TYPE caja_movimiento_tipo AS ENUM ('INGRESO', 'EGRESO', 'AJUSTE');
CREATE TYPE caja_movimiento_categoria AS ENUM (
    'VENTA',
    'COMPRA',
    'GASTO',
    'NOMINA',
    'BANCO',
    'CAMBIO',
    'AJUSTE',
    'OTRO'
);
CREATE TYPE cierre_caja_status AS ENUM ('ABIERTO', 'CERRADO', 'PENDIENTE');

COMMENT ON TYPE caja_movimiento_tipo IS 'Tipo de movimiento: INGRESO=Entrada efectivo, EGRESO=Salida efectivo, AJUSTE=Ajuste de cuadre';
COMMENT ON TYPE caja_movimiento_categoria IS 'Categoría del movimiento: VENTA, COMPRA, GASTO, NOMINA, BANCO, CAMBIO, AJUSTE, OTRO';
COMMENT ON TYPE cierre_caja_status IS 'Estado de cierre: ABIERTO=En curso, CERRADO=Cuadrado, PENDIENTE=Con descuadre';

-- ============================================================================
-- Tabla: caja_movimientos
-- ============================================================================

CREATE TABLE caja_movimientos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Tipo y categoría
    tipo caja_movimiento_tipo NOT NULL,
    categoria caja_movimiento_categoria NOT NULL,

    -- Importe
    importe NUMERIC(12, 2) NOT NULL,
    moneda CHAR(3) NOT NULL DEFAULT 'EUR',

    -- Descripción
    concepto VARCHAR(255) NOT NULL,
    notas TEXT,

    -- Referencia a documento origen
    ref_doc_type VARCHAR(50),
    ref_doc_id UUID,

    -- Multi-caja (opcional)
    caja_id UUID,

    -- Usuario responsable
    usuario_id UUID,

    -- Fecha
    fecha DATE NOT NULL,

    -- Relación con cierre
    cierre_id UUID REFERENCES cierres_caja(id) ON DELETE SET NULL,

    -- Auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_caja_movimientos_tenant_id ON caja_movimientos(tenant_id);
CREATE INDEX idx_caja_movimientos_fecha ON caja_movimientos(fecha);
CREATE INDEX idx_caja_movimientos_tipo ON caja_movimientos(tipo);
CREATE INDEX idx_caja_movimientos_categoria ON caja_movimientos(categoria);
CREATE INDEX idx_caja_movimientos_caja_id ON caja_movimientos(caja_id) WHERE caja_id IS NOT NULL;
CREATE INDEX idx_caja_movimientos_cierre_id ON caja_movimientos(cierre_id) WHERE cierre_id IS NOT NULL;
CREATE INDEX idx_caja_movimientos_ref_doc ON caja_movimientos(ref_doc_type, ref_doc_id) WHERE ref_doc_id IS NOT NULL;
CREATE INDEX idx_caja_movimientos_fecha_tenant ON caja_movimientos(fecha, tenant_id);

-- Comentarios
COMMENT ON TABLE caja_movimientos IS 'Movimientos de caja (ingresos, egresos, ajustes)';
COMMENT ON COLUMN caja_movimientos.tipo IS 'INGRESO (positivo), EGRESO (negativo), AJUSTE';
COMMENT ON COLUMN caja_movimientos.categoria IS 'Categoría del movimiento (VENTA, COMPRA, GASTO, etc.)';
COMMENT ON COLUMN caja_movimientos.importe IS 'Importe (positivo para ingresos, negativo para egresos)';
COMMENT ON COLUMN caja_movimientos.moneda IS 'Código moneda ISO 4217 (EUR, USD, etc.)';
COMMENT ON COLUMN caja_movimientos.concepto IS 'Descripción del movimiento';
COMMENT ON COLUMN caja_movimientos.ref_doc_type IS 'Tipo de documento origen (invoice, receipt, expense, payroll)';
COMMENT ON COLUMN caja_movimientos.ref_doc_id IS 'ID del documento origen';
COMMENT ON COLUMN caja_movimientos.caja_id IS 'ID de caja (para multi-caja/multi-punto)';
COMMENT ON COLUMN caja_movimientos.usuario_id IS 'Usuario que registró el movimiento';
COMMENT ON COLUMN caja_movimientos.cierre_id IS 'ID del cierre al que pertenece';

-- ============================================================================
-- Tabla: cierres_caja
-- ============================================================================

CREATE TABLE cierres_caja (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Fecha y caja
    fecha DATE NOT NULL,
    caja_id UUID,
    moneda CHAR(3) NOT NULL DEFAULT 'EUR',

    -- === SALDOS ===
    saldo_inicial NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_ingresos NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_egresos NUMERIC(12, 2) NOT NULL DEFAULT 0,
    saldo_teorico NUMERIC(12, 2) NOT NULL DEFAULT 0,
    saldo_real NUMERIC(12, 2) NOT NULL DEFAULT 0,
    diferencia NUMERIC(12, 2) NOT NULL DEFAULT 0,

    -- === ESTADO ===
    status cierre_caja_status NOT NULL DEFAULT 'ABIERTO',
    cuadrado BOOLEAN NOT NULL DEFAULT FALSE,

    -- === DETALLES ===
    detalles_billetes JSONB,
    notas TEXT,

    -- === USUARIOS ===
    abierto_por UUID,
    abierto_at TIMESTAMPTZ,
    cerrado_por UUID,
    cerrado_at TIMESTAMPTZ,

    -- Auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- === CONSTRAINTS ===
    CONSTRAINT cierres_caja_fecha_caja_unique
        UNIQUE (tenant_id, fecha, caja_id),
    CONSTRAINT cierres_caja_saldos_check
        CHECK (saldo_teorico = saldo_inicial + total_ingresos - total_egresos),
    CONSTRAINT cierres_caja_diferencia_check
        CHECK (diferencia = saldo_real - saldo_teorico)
);

-- Índices
CREATE INDEX idx_cierres_caja_tenant_id ON cierres_caja(tenant_id);
CREATE INDEX idx_cierres_caja_fecha ON cierres_caja(fecha);
CREATE INDEX idx_cierres_caja_status ON cierres_caja(status);
CREATE INDEX idx_cierres_caja_caja_id ON cierres_caja(caja_id) WHERE caja_id IS NOT NULL;
CREATE INDEX idx_cierres_caja_cuadrado ON cierres_caja(cuadrado) WHERE cuadrado = FALSE;
CREATE INDEX idx_cierres_caja_fecha_tenant ON cierres_caja(fecha, tenant_id);

-- Comentarios
COMMENT ON TABLE cierres_caja IS 'Cierres diarios de caja con conciliación';
COMMENT ON COLUMN cierres_caja.fecha IS 'Fecha del cierre';
COMMENT ON COLUMN cierres_caja.caja_id IS 'ID de caja (para multi-caja)';
COMMENT ON COLUMN cierres_caja.saldo_inicial IS 'Saldo al inicio del día';
COMMENT ON COLUMN cierres_caja.total_ingresos IS 'Suma de ingresos del día';
COMMENT ON COLUMN cierres_caja.total_egresos IS 'Suma de egresos del día (valor absoluto)';
COMMENT ON COLUMN cierres_caja.saldo_teorico IS 'Saldo teórico (inicial + ingresos - egresos)';
COMMENT ON COLUMN cierres_caja.saldo_real IS 'Efectivo contado físicamente';
COMMENT ON COLUMN cierres_caja.diferencia IS 'Diferencia (real - teórico)';
COMMENT ON COLUMN cierres_caja.status IS 'Estado: ABIERTO, CERRADO, PENDIENTE';
COMMENT ON COLUMN cierres_caja.cuadrado IS 'True si diferencia = 0';
COMMENT ON COLUMN cierres_caja.detalles_billetes IS 'Desglose de billetes y monedas contadas (JSON)';

-- ============================================================================
-- RLS (Row Level Security)
-- ============================================================================

ALTER TABLE caja_movimientos ENABLE ROW LEVEL SECURITY;
ALTER TABLE cierres_caja ENABLE ROW LEVEL SECURITY;

-- Políticas RLS para caja_movimientos
CREATE POLICY caja_movimientos_tenant_isolation ON caja_movimientos
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- Políticas RLS para cierres_caja
CREATE POLICY cierres_caja_tenant_isolation ON cierres_caja
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger para actualizar updated_at en cierres_caja
CREATE TRIGGER cierres_caja_updated_at
    BEFORE UPDATE ON cierres_caja
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- FUNCIONES
-- ============================================================================

-- Función para auto-calcular totales de cierre
CREATE OR REPLACE FUNCTION recalcular_totales_cierre(p_cierre_id UUID)
RETURNS void AS $$
DECLARE
    v_tenant_id UUID;
    v_fecha DATE;
    v_caja_id UUID;
    v_total_ingresos NUMERIC(12, 2);
    v_total_egresos NUMERIC(12, 2);
BEGIN
    -- Obtener datos del cierre
    SELECT tenant_id, fecha, caja_id
    INTO v_tenant_id, v_fecha, v_caja_id
    FROM cierres_caja
    WHERE id = p_cierre_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Cierre no encontrado: %', p_cierre_id;
    END IF;

    -- Calcular totales de movimientos
    SELECT
        COALESCE(SUM(importe) FILTER (WHERE importe > 0), 0),
        COALESCE(ABS(SUM(importe) FILTER (WHERE importe < 0)), 0)
    INTO v_total_ingresos, v_total_egresos
    FROM caja_movimientos
    WHERE tenant_id = v_tenant_id
      AND fecha = v_fecha
      AND (caja_id = v_caja_id OR (caja_id IS NULL AND v_caja_id IS NULL));

    -- Actualizar cierre
    UPDATE cierres_caja
    SET total_ingresos = v_total_ingresos,
        total_egresos = v_total_egresos,
        saldo_teorico = saldo_inicial + v_total_ingresos - v_total_egresos,
        diferencia = saldo_real - (saldo_inicial + v_total_ingresos - v_total_egresos),
        cuadrado = (saldo_real = saldo_inicial + v_total_ingresos - v_total_egresos)
    WHERE id = p_cierre_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION recalcular_totales_cierre IS 'Recalcula totales de un cierre basándose en movimientos';

-- Trigger para actualizar cierre cuando se agrega/modifica movimiento
CREATE OR REPLACE FUNCTION trigger_actualizar_cierre_movimiento()
RETURNS TRIGGER AS $$
BEGIN
    -- Si el movimiento está vinculado a un cierre, recalcular
    IF NEW.cierre_id IS NOT NULL THEN
        PERFORM recalcular_totales_cierre(NEW.cierre_id);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER caja_movimientos_actualizar_cierre
    AFTER INSERT OR UPDATE ON caja_movimientos
    FOR EACH ROW
    WHEN (NEW.cierre_id IS NOT NULL)
    EXECUTE FUNCTION trigger_actualizar_cierre_movimiento();

-- ============================================================================
-- VISTAS
-- ============================================================================

-- Vista: Resumen diario de caja por tenant
CREATE OR REPLACE VIEW v_caja_resumen_diario AS
SELECT
    tenant_id,
    fecha,
    caja_id,
    moneda,
    COUNT(*) as total_movimientos,
    SUM(CASE WHEN tipo = 'INGRESO' THEN importe ELSE 0 END) as total_ingresos,
    ABS(SUM(CASE WHEN tipo = 'EGRESO' THEN importe ELSE 0 END)) as total_egresos,
    SUM(importe) as saldo_neto
FROM caja_movimientos
GROUP BY tenant_id, fecha, caja_id, moneda
ORDER BY fecha DESC, tenant_id;

COMMENT ON VIEW v_caja_resumen_diario IS 'Resumen diario de movimientos de caja por tenant';

-- ============================================================================
-- DATOS INICIALES (Opcional)
-- ============================================================================

-- No se requieren datos iniciales para este módulo

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================

-- Log de migración
DO $$
BEGIN
    RAISE NOTICE 'Migración 2025-11-03_202_finance_caja aplicada exitosamente';
    RAISE NOTICE '- Tablas creadas: caja_movimientos, cierres_caja';
    RAISE NOTICE '- RLS habilitado en todas las tablas';
    RAISE NOTICE '- Índices de performance aplicados';
    RAISE NOTICE '- Función recalcular_totales_cierre() creada';
    RAISE NOTICE '- Vista v_caja_resumen_diario creada';
END $$;
