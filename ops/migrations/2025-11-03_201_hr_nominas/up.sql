-- ============================================================================
-- Migration: 2025-11-03_201_hr_nominas
-- Descripción: Sistema completo de nóminas con devengos, deducciones y conceptos
-- Autor: GestiQCloud Team
-- Fecha: 2025-11-03
-- ============================================================================

-- Crear tipos ENUM para nóminas
CREATE TYPE nomina_status AS ENUM ('DRAFT', 'APPROVED', 'PAID', 'CANCELLED');
CREATE TYPE nomina_tipo AS ENUM ('MENSUAL', 'EXTRA', 'FINIQUITO', 'ESPECIAL');

COMMENT ON TYPE nomina_status IS 'Estados de una nómina: DRAFT=Borrador, APPROVED=Aprobada, PAID=Pagada, CANCELLED=Cancelada';
COMMENT ON TYPE nomina_tipo IS 'Tipos de nómina: MENSUAL=Ordinaria, EXTRA=Paga extra, FINIQUITO=Liquidación, ESPECIAL=Pagos especiales';

-- ============================================================================
-- Tabla: nominas
-- ============================================================================

CREATE TABLE nominas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Numeración y referencias
    numero VARCHAR(50) NOT NULL UNIQUE,
    empleado_id UUID NOT NULL REFERENCES empleados(id) ON DELETE RESTRICT,

    -- Período
    periodo_mes INTEGER NOT NULL CHECK (periodo_mes >= 1 AND periodo_mes <= 12),
    periodo_ano INTEGER NOT NULL CHECK (periodo_ano >= 2020 AND periodo_ano <= 2100),
    tipo nomina_tipo NOT NULL DEFAULT 'MENSUAL',

    -- === DEVENGOS (positivos) ===
    salario_base NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (salario_base >= 0),
    complementos NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (complementos >= 0),
    horas_extra NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (horas_extra >= 0),
    otros_devengos NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (otros_devengos >= 0),
    total_devengado NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (total_devengado >= 0),

    -- === DEDUCCIONES (negativas) ===
    seg_social NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (seg_social >= 0),
    irpf NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (irpf >= 0),
    otras_deducciones NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (otras_deducciones >= 0),
    total_deducido NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (total_deducido >= 0),

    -- === TOTALES ===
    liquido_total NUMERIC(12, 2) NOT NULL DEFAULT 0,

    -- === PAGO ===
    fecha_pago DATE,
    metodo_pago VARCHAR(50),

    -- === ESTADO ===
    status nomina_status NOT NULL DEFAULT 'DRAFT',

    -- === INFORMACIÓN ADICIONAL ===
    notas TEXT,
    conceptos_json JSONB,

    -- === AUDITORÍA ===
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- === CONSTRAINTS ===
    CONSTRAINT nominas_periodo_empleado_tipo_unique
        UNIQUE (tenant_id, empleado_id, periodo_mes, periodo_ano, tipo)
);

-- Índices
CREATE INDEX idx_nominas_tenant_id ON nominas(tenant_id);
CREATE INDEX idx_nominas_empleado_id ON nominas(empleado_id);
CREATE INDEX idx_nominas_periodo ON nominas(periodo_ano, periodo_mes);
CREATE INDEX idx_nominas_status ON nominas(status);
CREATE INDEX idx_nominas_numero ON nominas(numero);
CREATE INDEX idx_nominas_fecha_pago ON nominas(fecha_pago) WHERE fecha_pago IS NOT NULL;

-- Comentarios
COMMENT ON TABLE nominas IS 'Nóminas mensuales de empleados con devengos, deducciones y totales';
COMMENT ON COLUMN nominas.numero IS 'Número único de nómina (NOM-YYYY-MM-NNNN)';
COMMENT ON COLUMN nominas.salario_base IS 'Salario base del período';
COMMENT ON COLUMN nominas.complementos IS 'Suma de complementos salariales (plus transporte, nocturnidad, etc.)';
COMMENT ON COLUMN nominas.horas_extra IS 'Pago por horas extraordinarias';
COMMENT ON COLUMN nominas.otros_devengos IS 'Otros devengos';
COMMENT ON COLUMN nominas.total_devengado IS 'Total devengado (suma de devengos)';
COMMENT ON COLUMN nominas.seg_social IS 'Cotización Seguridad Social (España) o IESS (Ecuador)';
COMMENT ON COLUMN nominas.irpf IS 'Retención IRPF (España) o Impuesto Renta (Ecuador)';
COMMENT ON COLUMN nominas.otras_deducciones IS 'Otras deducciones (anticipos, embargos, etc.)';
COMMENT ON COLUMN nominas.total_deducido IS 'Total deducido (suma de deducciones)';
COMMENT ON COLUMN nominas.liquido_total IS 'Líquido a pagar (devengos - deducciones)';
COMMENT ON COLUMN nominas.conceptos_json IS 'Detalle de conceptos en formato JSON';

-- ============================================================================
-- Tabla: nomina_conceptos
-- ============================================================================

CREATE TABLE nomina_conceptos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nomina_id UUID NOT NULL REFERENCES nominas(id) ON DELETE CASCADE,

    -- Tipo de concepto
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('DEVENGO', 'DEDUCCION')),
    codigo VARCHAR(50) NOT NULL,
    descripcion VARCHAR(255) NOT NULL,

    -- Importe
    importe NUMERIC(12, 2) NOT NULL CHECK (importe >= 0),

    -- Configuración
    es_base BOOLEAN NOT NULL DEFAULT TRUE,

    -- Auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_nomina_conceptos_nomina_id ON nomina_conceptos(nomina_id);
CREATE INDEX idx_nomina_conceptos_tipo ON nomina_conceptos(tipo);
CREATE INDEX idx_nomina_conceptos_codigo ON nomina_conceptos(codigo);

-- Comentarios
COMMENT ON TABLE nomina_conceptos IS 'Conceptos individuales de nómina (devengos y deducciones)';
COMMENT ON COLUMN nomina_conceptos.tipo IS 'DEVENGO (positivo) o DEDUCCION (negativo)';
COMMENT ON COLUMN nomina_conceptos.codigo IS 'Código del concepto (ej: PLUS_TRANS, ANTICIPO)';
COMMENT ON COLUMN nomina_conceptos.importe IS 'Cantidad del concepto (siempre positivo)';
COMMENT ON COLUMN nomina_conceptos.es_base IS 'Si computa para base de cotización';

-- ============================================================================
-- Tabla: nomina_plantillas
-- ============================================================================

CREATE TABLE nomina_plantillas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    empleado_id UUID NOT NULL REFERENCES empleados(id) ON DELETE CASCADE,

    -- Configuración
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    conceptos_json JSONB NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    -- Auditoría
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT nomina_plantillas_tenant_empleado_nombre_unique
        UNIQUE (tenant_id, empleado_id, nombre)
);

-- Índices
CREATE INDEX idx_nomina_plantillas_tenant_id ON nomina_plantillas(tenant_id);
CREATE INDEX idx_nomina_plantillas_empleado_id ON nomina_plantillas(empleado_id);
CREATE INDEX idx_nomina_plantillas_activo ON nomina_plantillas(activo) WHERE activo = TRUE;

-- Comentarios
COMMENT ON TABLE nomina_plantillas IS 'Plantillas de conceptos estándar para generar nóminas automáticamente';
COMMENT ON COLUMN nomina_plantillas.nombre IS 'Nombre de la plantilla';
COMMENT ON COLUMN nomina_plantillas.conceptos_json IS 'Lista de conceptos con tipo, código, descripción e importe';
COMMENT ON COLUMN nomina_plantillas.activo IS 'Plantilla activa (para uso automático)';

-- ============================================================================
-- RLS (Row Level Security)
-- ============================================================================

ALTER TABLE nominas ENABLE ROW LEVEL SECURITY;
ALTER TABLE nomina_conceptos ENABLE ROW LEVEL SECURITY;
ALTER TABLE nomina_plantillas ENABLE ROW LEVEL SECURITY;

-- Políticas RLS para nominas
CREATE POLICY nominas_tenant_isolation ON nominas
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- Políticas RLS para nomina_conceptos (via nominas)
CREATE POLICY nomina_conceptos_tenant_isolation ON nomina_conceptos
    USING (
        EXISTS (
            SELECT 1 FROM nominas
            WHERE nominas.id = nomina_conceptos.nomina_id
            AND nominas.tenant_id::text = current_setting('app.tenant_id', TRUE)
        )
    );

-- Políticas RLS para nomina_plantillas
CREATE POLICY nomina_plantillas_tenant_isolation ON nomina_plantillas
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger para actualizar updated_at en nominas
CREATE TRIGGER nominas_updated_at
    BEFORE UPDATE ON nominas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger para actualizar updated_at en nomina_plantillas
CREATE TRIGGER nomina_plantillas_updated_at
    BEFORE UPDATE ON nomina_plantillas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- FUNCIONES
-- ============================================================================

-- Función para validar totales de nómina (trigger opcional)
CREATE OR REPLACE FUNCTION validate_nomina_totals()
RETURNS TRIGGER AS $$
BEGIN
    -- Validar que total_devengado sea la suma correcta
    IF NEW.total_devengado != (NEW.salario_base + NEW.complementos + NEW.horas_extra + NEW.otros_devengos) THEN
        RAISE EXCEPTION 'Total devengado no coincide con la suma de devengos';
    END IF;

    -- Validar que total_deducido sea la suma correcta
    IF NEW.total_deducido != (NEW.seg_social + NEW.irpf + NEW.otras_deducciones) THEN
        RAISE EXCEPTION 'Total deducido no coincide con la suma de deducciones';
    END IF;

    -- Validar que líquido total sea correcto
    IF NEW.liquido_total != (NEW.total_devengado - NEW.total_deducido) THEN
        RAISE EXCEPTION 'Líquido total no coincide con devengos - deducciones';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger de validación (opcional, comentado para permitir flexibilidad)
-- CREATE TRIGGER nominas_validate_totals
--     BEFORE INSERT OR UPDATE ON nominas
--     FOR EACH ROW
--     EXECUTE FUNCTION validate_nomina_totals();

-- ============================================================================
-- DATOS INICIALES (Opcional)
-- ============================================================================

-- Conceptos estándar España
-- (Se pueden cargar desde catálogo si existe tabla de conceptos)

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================

-- Log de migración
DO $$
BEGIN
    RAISE NOTICE 'Migración 2025-11-03_201_hr_nominas aplicada exitosamente';
    RAISE NOTICE '- Tablas creadas: nominas, nomina_conceptos, nomina_plantillas';
    RAISE NOTICE '- RLS habilitado en todas las tablas';
    RAISE NOTICE '- Índices de performance aplicados';
END $$;
