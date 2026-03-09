CREATE TABLE IF NOT EXISTS imp_batch_import (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    usuario_id VARCHAR(100),
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    total_items INTEGER NOT NULL DEFAULT 0,
    force_reprocess BOOLEAN NOT NULL DEFAULT FALSE,
    recipe_snapshot_id UUID REFERENCES icu_recipe_snapshot(id) ON DELETE SET NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_imp_batch_import_tenant_id
    ON imp_batch_import (tenant_id);

CREATE INDEX IF NOT EXISTS ix_imp_batch_import_estado
    ON imp_batch_import (estado);

CREATE TABLE IF NOT EXISTS imp_batch_item (
    id UUID PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES imp_batch_import(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    documento_id UUID REFERENCES imp_documento(id) ON DELETE SET NULL,
    nombre_archivo VARCHAR(500) NOT NULL,
    tamanio_bytes INTEGER NOT NULL DEFAULT 0,
    hash_sha256 VARCHAR(64),
    orden INTEGER NOT NULL DEFAULT 0,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    error_detalle TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_imp_batch_item_batch_id
    ON imp_batch_item (batch_id);

CREATE INDEX IF NOT EXISTS ix_imp_batch_item_documento_id
    ON imp_batch_item (documento_id);

CREATE INDEX IF NOT EXISTS ix_imp_batch_item_tenant_id
    ON imp_batch_item (tenant_id);

CREATE INDEX IF NOT EXISTS ix_imp_batch_item_hash_sha256
    ON imp_batch_item (hash_sha256);
