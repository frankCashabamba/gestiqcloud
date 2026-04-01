-- imp_column_candidate: vocabulario de nombres de columna vistos en documentos procesados
-- que todavía no tienen un campo canónico asignado.
--
-- El sistema la alimenta automáticamente en tiempo de procesamiento.
-- Un administrador puede asignar canonical_field y el sistema lo promoverá a imp_field_alias.
-- Seguridad: el código rechaza SQL keywords y patrones de inyección antes de insertar.

BEGIN;

CREATE TABLE IF NOT EXISTS imp_column_candidate (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    alias         VARCHAR(100) NOT NULL,
    alias_norm    VARCHAR(100) NOT NULL,
    doc_type      VARCHAR(50),
    tenant_id     UUID         REFERENCES tenants(id) ON DELETE CASCADE,
    seen_count    INTEGER      NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_seen_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    -- Asignación posterior por un administrador:
    canonical_field VARCHAR(100) REFERENCES imp_canonical_field(name) ON DELETE SET NULL,
    assigned_at   TIMESTAMPTZ,
    assigned_by   VARCHAR(100)
);

-- Índice único parcial para tenant_id NULL (alias globales)
CREATE UNIQUE INDEX IF NOT EXISTS imp_column_candidate_global_uq
    ON imp_column_candidate (alias_norm)
    WHERE tenant_id IS NULL;

-- Índice único parcial para alias por tenant
CREATE UNIQUE INDEX IF NOT EXISTS imp_column_candidate_tenant_uq
    ON imp_column_candidate (alias_norm, tenant_id)
    WHERE tenant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS imp_column_candidate_unassigned_idx
    ON imp_column_candidate (canonical_field, seen_count DESC)
    WHERE canonical_field IS NULL;

COMMIT;
