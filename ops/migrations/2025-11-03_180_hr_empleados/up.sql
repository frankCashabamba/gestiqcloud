-- Migration: 2025-11-03_180_hr_empleados
-- Description: Base tables for HR module (empleados + vacaciones)

SET row_security = off;

-- Ensure helper trigger function exists (idempotent)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Tabla: empleados
-- ============================================================================
CREATE TABLE IF NOT EXISTS empleados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    usuario_id UUID REFERENCES auth_user(id) ON DELETE SET NULL,
    codigo VARCHAR(50),
    nombre VARCHAR(255) NOT NULL,
    apellidos VARCHAR(255),
    documento VARCHAR(50),
    fecha_nacimiento DATE,
    fecha_alta DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_baja DATE,
    cargo VARCHAR(100),
    departamento VARCHAR(100),
    salario_base NUMERIC(12,2),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_empleados_tenant ON empleados(tenant_id);
CREATE INDEX IF NOT EXISTS idx_empleados_usuario ON empleados(usuario_id);
CREATE INDEX IF NOT EXISTS idx_empleados_activo ON empleados(activo) WHERE activo = TRUE;
CREATE INDEX IF NOT EXISTS idx_empleados_departamento ON empleados(departamento);

COMMENT ON TABLE empleados IS 'Catálogo de empleados por tenant';
COMMENT ON COLUMN empleados.salario_base IS 'Salario mensual base registrado para el empleado';

ALTER TABLE empleados ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_empleados ON empleados;
CREATE POLICY tenant_isolation_empleados ON empleados
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Tabla: vacaciones
-- ============================================================================
CREATE TABLE IF NOT EXISTS vacaciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    empleado_id UUID NOT NULL REFERENCES empleados(id) ON DELETE CASCADE,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    dias INTEGER NOT NULL CHECK (dias > 0),
    estado VARCHAR(20) NOT NULL DEFAULT 'solicitada',
    aprobado_por UUID,
    notas TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vacaciones_tenant ON vacaciones(tenant_id);
CREATE INDEX IF NOT EXISTS idx_vacaciones_empleado ON vacaciones(empleado_id);
CREATE INDEX IF NOT EXISTS idx_vacaciones_estado ON vacaciones(estado);

COMMENT ON TABLE vacaciones IS 'Solicitudes de vacaciones asociadas a empleados de un tenant';

ALTER TABLE vacaciones ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_vacaciones ON vacaciones;
CREATE POLICY tenant_isolation_vacaciones ON vacaciones
    USING (
        EXISTS (
            SELECT 1
            FROM empleados e
            WHERE e.id = vacaciones.empleado_id
              AND e.tenant_id::text = current_setting('app.tenant_id', TRUE)
        )
    );

-- ============================================================================
-- Triggers
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'empleados_updated_at'
    ) THEN
        CREATE TRIGGER empleados_updated_at
            BEFORE UPDATE ON empleados
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'vacaciones_updated_at'
    ) THEN
        CREATE TRIGGER vacaciones_updated_at
            BEFORE UPDATE ON vacaciones
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;
