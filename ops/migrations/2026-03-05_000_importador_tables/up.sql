-- Módulo Importador Contable Universal v1.3
-- Flujo: Upload → OCR/AI Auto-Classify → Preview → Confirm
-- Formatos: PDF, JPG, PNG, XLSX, XLS, CSV, XML (UBL 2.1), TXT
-- Recipe system: Recipe → Draft → Snapshot → Execution

CREATE TABLE IF NOT EXISTS imp_documento (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                 UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nombre_archivo            VARCHAR(500) NOT NULL,
    tipo_archivo              VARCHAR(10) NOT NULL,
    tamanio_bytes             INTEGER NOT NULL DEFAULT 0,

    -- AI classification
    tipo_documento_detectado  VARCHAR(50),
    confianza_clasificacion   DOUBLE PRECISION,
    requiere_revision         BOOLEAN NOT NULL DEFAULT FALSE,

    -- Extracted / confirmed data
    texto_ocr                 TEXT,
    datos_extraidos           JSONB,
    datos_confirmados         JSONB,

    -- Status
    estado                    VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    error_detalle             TEXT,

    -- Detected metadata
    proveedor_detectado       VARCHAR(255),
    ruc_detectado             VARCHAR(20),
    monto_total               DOUBLE PRECISION,
    moneda                    VARCHAR(5),
    fecha_documento           VARCHAR(20),

    usuario_id                VARCHAR(100),
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_imp_doc_tenant   ON imp_documento(tenant_id);
CREATE INDEX IF NOT EXISTS idx_imp_doc_estado   ON imp_documento(estado);

CREATE TABLE IF NOT EXISTS imp_log_cambios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    documento_id    UUID NOT NULL REFERENCES imp_documento(id) ON DELETE CASCADE,
    accion          VARCHAR(30) NOT NULL,
    detalle         JSONB,
    usuario_id      VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_imp_log_doc ON imp_log_cambios(documento_id);

-- =====================================================
-- Recipe system tables (v1.3)
-- =====================================================

CREATE TABLE IF NOT EXISTS icu_recipe (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    is_public       BOOLEAN NOT NULL DEFAULT FALSE,
    created_by      VARCHAR(100),
    archived        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_icu_recipe_tenant ON icu_recipe(tenant_id);

CREATE TABLE IF NOT EXISTS icu_recipe_draft (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    recipe_id       UUID NOT NULL REFERENCES icu_recipe(id) ON DELETE CASCADE,
    prompt_system   TEXT,
    prompt_user     TEXT,
    model_config    JSONB,
    updated_by      VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_icu_draft_recipe ON icu_recipe_draft(recipe_id);

CREATE TABLE IF NOT EXISTS icu_recipe_snapshot (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    recipe_id       UUID NOT NULL REFERENCES icu_recipe(id) ON DELETE CASCADE,
    draft_id        UUID REFERENCES icu_recipe_draft(id) ON DELETE SET NULL,
    version_tag     VARCHAR(50),
    content_json    JSONB NOT NULL,
    created_by      VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_icu_snapshot_recipe ON icu_recipe_snapshot(recipe_id);

-- =====================================================
-- Add recipe/AI columns to imp_documento
-- =====================================================

ALTER TABLE imp_documento
    ADD COLUMN IF NOT EXISTS recipe_snapshot_id UUID REFERENCES icu_recipe_snapshot(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS llm_model          VARCHAR(50),
    ADD COLUMN IF NOT EXISTS raw_ai_json        JSONB;
