-- ============================================================================
-- Migration: 2025-11-03_203_accounting
-- Descripción: Sistema completo de contabilidad general (PGC España + Ecuador)
-- Autor: GestiQCloud Team
-- Fecha: 2025-11-03
-- ============================================================================

-- Crear función helper si no existe
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear tipos ENUM para contabilidad
DO $$ BEGIN
  CREATE TYPE cuenta_tipo AS ENUM ('ACTIVO', 'PASIVO', 'PATRIMONIO', 'INGRESO', 'GASTO');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE asiento_status AS ENUM ('BORRADOR', 'VALIDADO', 'CONTABILIZADO', 'ANULADO');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

COMMENT ON TYPE cuenta_tipo IS 'Tipo de cuenta: ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO';
COMMENT ON TYPE asiento_status IS 'Estado de asiento: BORRADOR=Sin validar, VALIDADO=Cuadrado, CONTABILIZADO=Posted, ANULADO=Cancelado';

-- ============================================================================
-- Tabla: plan_cuentas
-- ============================================================================

CREATE TABLE IF NOT EXISTS plan_cuentas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Código y nombre
    codigo VARCHAR(20) NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,

    -- Clasificación
    tipo cuenta_tipo NOT NULL,
    nivel INTEGER NOT NULL CHECK (nivel >= 1 AND nivel <= 4),

    -- Jerarquía
    padre_id UUID REFERENCES plan_cuentas(id) ON DELETE CASCADE,

    -- Configuración
    imputable BOOLEAN NOT NULL DEFAULT TRUE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    -- Saldos (calculados)
    saldo_debe NUMERIC(14, 2) NOT NULL DEFAULT 0,
    saldo_haber NUMERIC(14, 2) NOT NULL DEFAULT 0,
    saldo NUMERIC(14, 2) NOT NULL DEFAULT 0,

    -- Auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- === CONSTRAINTS ===
    CONSTRAINT plan_cuentas_tenant_codigo_unique UNIQUE (tenant_id, codigo)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_plan_cuentas_tenant_id ON plan_cuentas(tenant_id);
CREATE INDEX IF NOT EXISTS idx_plan_cuentas_codigo ON plan_cuentas(codigo);
CREATE INDEX IF NOT EXISTS idx_plan_cuentas_tipo ON plan_cuentas(tipo);
CREATE INDEX IF NOT EXISTS idx_plan_cuentas_padre_id ON plan_cuentas(padre_id) WHERE padre_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_plan_cuentas_activo ON plan_cuentas(activo) WHERE activo = TRUE;
CREATE INDEX IF NOT EXISTS idx_plan_cuentas_imputable ON plan_cuentas(imputable) WHERE imputable = TRUE;

-- Comentarios
COMMENT ON TABLE plan_cuentas IS 'Plan de cuentas contable jerárquico';
COMMENT ON COLUMN plan_cuentas.codigo IS 'Código de la cuenta (ej: 5700001)';
COMMENT ON COLUMN plan_cuentas.tipo IS 'ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO';
COMMENT ON COLUMN plan_cuentas.nivel IS 'Nivel jerárquico (1=Grupo, 2=Subgrupo, 3=Cuenta, 4=Subcuenta)';
COMMENT ON COLUMN plan_cuentas.padre_id IS 'ID de la cuenta padre (NULL si es nivel 1)';
COMMENT ON COLUMN plan_cuentas.imputable IS 'Si permite movimientos directos (TRUE para subcuentas)';
COMMENT ON COLUMN plan_cuentas.saldo_debe IS 'Saldo acumulado debe';
COMMENT ON COLUMN plan_cuentas.saldo_haber IS 'Saldo acumulado haber';
COMMENT ON COLUMN plan_cuentas.saldo IS 'Saldo neto (debe - haber)';

-- ============================================================================
-- Tabla: asientos_contables
-- ============================================================================

CREATE TABLE IF NOT EXISTS asientos_contables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Numeración
    numero VARCHAR(50) NOT NULL UNIQUE,

    -- Fecha y tipo
    fecha DATE NOT NULL,
    tipo VARCHAR(50) NOT NULL DEFAULT 'OPERACIONES',

    -- Descripción
    descripcion TEXT NOT NULL,

    -- Totales
    debe_total NUMERIC(14, 2) NOT NULL DEFAULT 0,
    haber_total NUMERIC(14, 2) NOT NULL DEFAULT 0,
    cuadrado BOOLEAN NOT NULL DEFAULT FALSE,

    -- Estado
    status asiento_status NOT NULL DEFAULT 'BORRADOR',

    -- Referencia a documento origen
    ref_doc_type VARCHAR(50),
    ref_doc_id UUID,

    -- Auditoría
    created_by UUID,
    contabilizado_by UUID,
    contabilizado_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_asientos_contables_tenant_id ON asientos_contables(tenant_id);
CREATE INDEX IF NOT EXISTS idx_asientos_contables_numero ON asientos_contables(numero);
CREATE INDEX IF NOT EXISTS idx_asientos_contables_fecha ON asientos_contables(fecha);
CREATE INDEX IF NOT EXISTS idx_asientos_contables_status ON asientos_contables(status);
CREATE INDEX IF NOT EXISTS idx_asientos_contables_tipo ON asientos_contables(tipo);
CREATE INDEX IF NOT EXISTS idx_asientos_contables_ref_doc ON asientos_contables(ref_doc_type, ref_doc_id) WHERE ref_doc_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_asientos_contables_fecha_tenant ON asientos_contables(fecha, tenant_id);

-- Comentarios
COMMENT ON TABLE asientos_contables IS 'Asientos contables (libro diario)';
COMMENT ON COLUMN asientos_contables.numero IS 'Número único (ASI-YYYY-NNNN)';
COMMENT ON COLUMN asientos_contables.tipo IS 'APERTURA, OPERACIONES, REGULARIZACION, CIERRE';
COMMENT ON COLUMN asientos_contables.debe_total IS 'Suma total del debe';
COMMENT ON COLUMN asientos_contables.haber_total IS 'Suma total del haber';
COMMENT ON COLUMN asientos_contables.cuadrado IS 'True si debe = haber';
COMMENT ON COLUMN asientos_contables.status IS 'Estado del asiento';
COMMENT ON COLUMN asientos_contables.ref_doc_type IS 'Tipo de documento origen (invoice, payment, etc.)';

-- ============================================================================
-- Tabla: asiento_lineas
-- ============================================================================

CREATE TABLE IF NOT EXISTS asiento_lineas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Referencias
    asiento_id UUID NOT NULL REFERENCES asientos_contables(id) ON DELETE CASCADE,
    cuenta_id UUID NOT NULL REFERENCES plan_cuentas(id) ON DELETE RESTRICT,

    -- Importes (solo uno debe tener valor)
    debe NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (debe >= 0),
    haber NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (haber >= 0),

    -- Descripción
    descripcion VARCHAR(255),

    -- Orden
    orden INTEGER NOT NULL DEFAULT 0,

    -- Auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- === CONSTRAINTS ===
    CONSTRAINT asiento_lineas_debe_o_haber_check
        CHECK ((debe > 0 AND haber = 0) OR (haber > 0 AND debe = 0))
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_asiento_lineas_asiento_id ON asiento_lineas(asiento_id);
CREATE INDEX IF NOT EXISTS idx_asiento_lineas_cuenta_id ON asiento_lineas(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_asiento_lineas_orden ON asiento_lineas(orden);

-- Comentarios
COMMENT ON TABLE asiento_lineas IS 'Líneas de asientos contables (movimientos)';
COMMENT ON COLUMN asiento_lineas.debe IS 'Importe al debe (0 si es haber)';
COMMENT ON COLUMN asiento_lineas.haber IS 'Importe al haber (0 si es debe)';
COMMENT ON COLUMN asiento_lineas.orden IS 'Orden dentro del asiento';

-- ============================================================================
-- RLS (Row Level Security)
-- ============================================================================

ALTER TABLE plan_cuentas ENABLE ROW LEVEL SECURITY;
ALTER TABLE asientos_contables ENABLE ROW LEVEL SECURITY;

-- RLS para plan_cuentas
DROP POLICY IF EXISTS plan_cuentas_tenant_isolation ON plan_cuentas;
CREATE POLICY plan_cuentas_tenant_isolation ON plan_cuentas
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- RLS para asientos_contables
DROP POLICY IF EXISTS asientos_contables_tenant_isolation ON asientos_contables;
CREATE POLICY asientos_contables_tenant_isolation ON asientos_contables
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- RLS para asiento_lineas (via asientos_contables)
-- No necesita RLS directo porque se accede siempre via asiento

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger para updated_at
DROP TRIGGER IF EXISTS plan_cuentas_updated_at ON plan_cuentas;
CREATE TRIGGER plan_cuentas_updated_at
    BEFORE UPDATE ON plan_cuentas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS asientos_contables_updated_at ON asientos_contables;
CREATE TRIGGER asientos_contables_updated_at
    BEFORE UPDATE ON asientos_contables
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- FUNCIONES
-- ============================================================================

-- Función para recalcular saldos de cuenta
CREATE OR REPLACE FUNCTION recalcular_saldos_cuenta(p_cuenta_id UUID)
RETURNS void AS $$
DECLARE
    v_debe NUMERIC(14, 2);
    v_haber NUMERIC(14, 2);
BEGIN
    -- Calcular totales desde líneas de asientos contabilizados
    SELECT
        COALESCE(SUM(debe), 0),
        COALESCE(SUM(haber), 0)
    INTO v_debe, v_haber
    FROM asiento_lineas al
    INNER JOIN asientos_contables ac ON al.asiento_id = ac.id
    WHERE al.cuenta_id = p_cuenta_id
      AND ac.status = 'CONTABILIZADO';

    -- Actualizar saldos
    UPDATE plan_cuentas
    SET saldo_debe = v_debe,
        saldo_haber = v_haber,
        saldo = v_debe - v_haber
    WHERE id = p_cuenta_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION recalcular_saldos_cuenta IS 'Recalcula saldos de una cuenta desde asientos contabilizados';

-- Función para validar asiento cuadrado
CREATE OR REPLACE FUNCTION validar_asiento_cuadrado()
RETURNS TRIGGER AS $$
DECLARE
    v_debe NUMERIC(14, 2);
    v_haber NUMERIC(14, 2);
    v_cuadrado BOOLEAN;
BEGIN
    -- Calcular totales
    SELECT
        COALESCE(SUM(debe), 0),
        COALESCE(SUM(haber), 0)
    INTO v_debe, v_haber
    FROM asiento_lineas
    WHERE asiento_id = NEW.id;

    v_cuadrado := ABS(v_debe - v_haber) < 0.01;

    -- Actualizar asiento
    UPDATE asientos_contables
    SET debe_total = v_debe,
        haber_total = v_haber,
        cuadrado = v_cuadrado
    WHERE id = NEW.id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para validar asiento tras insertar/actualizar líneas
DROP TRIGGER IF EXISTS asiento_lineas_validar_cuadre ON asiento_lineas;
CREATE TRIGGER asiento_lineas_validar_cuadre
    AFTER INSERT OR UPDATE OR DELETE ON asiento_lineas
    FOR EACH ROW
    EXECUTE FUNCTION validar_asiento_cuadrado();

-- ============================================================================
-- DATOS INICIALES - Plan Contable Básico
-- ============================================================================

-- Se cargará desde script Python específico por país
-- Ver: scripts/load_plan_contable_es.py
-- Ver: scripts/load_plan_contable_ec.py

-- ============================================================================
-- VISTAS
-- ============================================================================

-- Vista: Balance resumido por tipo
CREATE OR REPLACE VIEW v_balance_resumido AS
SELECT
    tenant_id,
    tipo,
    SUM(saldo_debe) as total_debe,
    SUM(saldo_haber) as total_haber,
    SUM(saldo) as saldo_neto
FROM plan_cuentas
WHERE activo = TRUE
GROUP BY tenant_id, tipo
ORDER BY tenant_id, tipo;

COMMENT ON VIEW v_balance_resumido IS 'Balance resumido por tipo de cuenta';

-- Vista: Asientos pendientes de contabilizar
CREATE OR REPLACE VIEW v_asientos_pendientes AS
SELECT
    id,
    tenant_id,
    numero,
    fecha,
    tipo,
    descripcion,
    debe_total,
    haber_total,
    cuadrado,
    status,
    created_at
FROM asientos_contables
WHERE status IN ('BORRADOR', 'VALIDADO')
ORDER BY fecha DESC, numero DESC;

COMMENT ON VIEW v_asientos_pendientes IS 'Asientos pendientes de contabilizar';

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================

-- Log de migración
DO $$
BEGIN
    RAISE NOTICE 'Migración 2025-11-03_203_accounting aplicada exitosamente';
    RAISE NOTICE '- Tablas creadas: plan_cuentas, asientos_contables, asiento_lineas';
    RAISE NOTICE '- RLS habilitado en plan_cuentas y asientos_contables';
    RAISE NOTICE '- Índices de performance aplicados';
    RAISE NOTICE '- Función recalcular_saldos_cuenta() creada';
    RAISE NOTICE '- Vistas v_balance_resumido y v_asientos_pendientes creadas';
    RAISE NOTICE '- Sistema contable completo operativo';
END $$;
