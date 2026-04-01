-- Migración: imp_vendor_snapshot
-- Asocia proveedores (por RUC y/o nombre normalizado) a snapshots de recetas.
-- Alimenta la capa L4 del pre-clasificador: cuando se reconoce el RUC de un
-- proveedor en el texto OCR antes de llamar a la IA, se reutiliza el snapshot
-- ya aprendido para ese proveedor.

CREATE TABLE IF NOT EXISTS imp_vendor_snapshot (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID        NOT NULL,
    ruc                 VARCHAR(30) NULL,
    vendor_norm         VARCHAR(200) NULL,
    recipe_snapshot_id  UUID        NOT NULL,
    confirmed_count     INTEGER     NOT NULL DEFAULT 1,
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active              BOOLEAN     NOT NULL DEFAULT TRUE
);

-- Índice único por tenant + RUC (cuando existe)
CREATE UNIQUE INDEX IF NOT EXISTS imp_vendor_snapshot_ruc_uidx
    ON imp_vendor_snapshot (tenant_id, ruc)
    WHERE ruc IS NOT NULL;

-- Índice único por tenant + vendor_norm (cuando existe)
CREATE UNIQUE INDEX IF NOT EXISTS imp_vendor_snapshot_vendor_uidx
    ON imp_vendor_snapshot (tenant_id, vendor_norm)
    WHERE vendor_norm IS NOT NULL;

-- Índice para lookup por snapshot
CREATE INDEX IF NOT EXISTS imp_vendor_snapshot_snapshot_idx
    ON imp_vendor_snapshot (recipe_snapshot_id);
