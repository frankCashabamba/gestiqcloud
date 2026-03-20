-- Líneas de staging: una fila por línea/fila del fichero importado.
-- Se crean una sola vez al subir el fichero (primera iteración).
-- Las iteraciones posteriores solo actualizan su estado.
CREATE TABLE IF NOT EXISTS imp_staging_line (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    documento_id    UUID        NOT NULL REFERENCES imp_documento(id) ON DELETE CASCADE,

    line_number     INTEGER     NOT NULL,
    sheet_name      VARCHAR(200),

    -- Datos tal como venían en el fichero (nunca se modifican)
    raw_data        JSONB       NOT NULL DEFAULT '{}',
    -- Datos después de mapeo y normalización (se actualiza en cada iteración)
    normalized_data JSONB,

    -- Estados del ciclo de vida de la línea
    estado          VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    -- PENDING  → no procesada
    -- VALID    → validada, lista para importar
    -- IMPORTED → importada correctamente
    -- INVALID  → tiene errores
    -- REVIEW   → marcada para revisión
    -- SKIPPED  → omitida intencionalmente
    -- REPROCESS→ marcada por usuario para reprocesar

    -- Referencia al registro creado en el destino
    target_table    VARCHAR(50),
    target_id       UUID,

    -- Error activo en esta línea
    error_code      VARCHAR(80) REFERENCES imp_error_code(code) ON DELETE SET NULL,
    error_detail    TEXT,

    -- Campos específicos en revisión (NULL = todos)
    campos_revision TEXT[],

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    imported_at     TIMESTAMPTZ,

    UNIQUE (documento_id, line_number, sheet_name)
);

CREATE INDEX ON imp_staging_line (documento_id, estado);
CREATE INDEX ON imp_staging_line (documento_id, line_number);
CREATE INDEX ON imp_staging_line (target_table, target_id) WHERE target_id IS NOT NULL;
CREATE INDEX ON imp_staging_line (error_code) WHERE error_code IS NOT NULL;

-- Iteraciones: cada pasada del fichero queda registrada
CREATE TABLE IF NOT EXISTS imp_iteration (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    documento_id    UUID        NOT NULL REFERENCES imp_documento(id) ON DELETE CASCADE,

    iteration_num   INTEGER     NOT NULL DEFAULT 1,

    scope           VARCHAR(20) NOT NULL DEFAULT 'ALL',
    -- ALL       → todos los pendientes/fallidos
    -- SELECTIVE → subconjunto definido en scope_filter
    scope_filter    JSONB,

    -- Métricas
    lines_attempted INTEGER     NOT NULL DEFAULT 0,
    lines_imported  INTEGER     NOT NULL DEFAULT 0,
    lines_errored   INTEGER     NOT NULL DEFAULT 0,
    lines_skipped   INTEGER     NOT NULL DEFAULT 0,

    prev_iteration_id UUID      REFERENCES imp_iteration(id),
    improvement     BOOLEAN,

    llm_model       VARCHAR(50),
    snapshot_id     UUID        REFERENCES icu_recipe_snapshot(id) ON DELETE SET NULL,

    estado          VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
    -- RUNNING, DONE, PARTIAL, NO_IMPROVEMENT, ABORTED

    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    initiated_by    VARCHAR(100),
    notes           TEXT
);

CREATE INDEX ON imp_iteration (documento_id, iteration_num);
CREATE INDEX ON imp_iteration (documento_id, estado);

-- Log histórico de errores por línea entre iteraciones
CREATE TABLE IF NOT EXISTS imp_line_error_log (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    staging_line_id UUID        NOT NULL REFERENCES imp_staging_line(id) ON DELETE CASCADE,
    iteration_id    UUID        NOT NULL REFERENCES imp_iteration(id) ON DELETE CASCADE,
    error_code      VARCHAR(80) NOT NULL,
    error_detail    TEXT,
    field_name      VARCHAR(100),
    resolved        BOOLEAN     NOT NULL DEFAULT FALSE,
    resolved_at     TIMESTAMPTZ,
    resolved_by     VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON imp_line_error_log (staging_line_id);
CREATE INDEX ON imp_line_error_log (iteration_id);
CREATE INDEX ON imp_line_error_log (error_code, resolved);

-- Sesiones de revisión selectiva creadas por el usuario
CREATE TABLE IF NOT EXISTS imp_review_session (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    documento_id    UUID        NOT NULL REFERENCES imp_documento(id) ON DELETE CASCADE,

    initiated_by    VARCHAR(100) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ,

    -- Filtros que definen el scope de la revisión
    filter_estados  TEXT[]      NOT NULL DEFAULT '{}',
    filter_error_codes TEXT[]   NOT NULL DEFAULT '{}',
    filter_campos   TEXT[]      NOT NULL DEFAULT '{}',
    filter_lines    INTEGER[]   NOT NULL DEFAULT '{}',
    filter_sheet    VARCHAR(200),

    -- Cuántas líneas quedaron en scope (calculado al crear la sesión)
    preview_count   INTEGER     NOT NULL DEFAULT 0,

    estado          VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    -- PENDING, RUNNING, DONE, CANCELLED
    linked_iteration_id UUID    REFERENCES imp_iteration(id) ON DELETE SET NULL
);

CREATE INDEX ON imp_review_session (documento_id, estado);

-- Vínculos entre documentos (mismo nombre, hash distinto = nueva versión)
CREATE TABLE IF NOT EXISTS imp_documento_successor (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    predecessor_id  UUID        NOT NULL REFERENCES imp_documento(id) ON DELETE CASCADE,
    successor_id    UUID        NOT NULL REFERENCES imp_documento(id) ON DELETE CASCADE,
    reason          VARCHAR(50) NOT NULL DEFAULT 'same_name_new_hash',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (predecessor_id, successor_id)
);
