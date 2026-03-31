-- Pre-classifier tables: filename patterns + header->doc_type mappings
-- Self-feeding: confidence updates automatically from document confirmations

BEGIN;

-- --- imp_filename_pattern ---------------------------------------------------
-- Regex patterns (against normalized filename stem) -> doc_type
-- source='seed': shipped with the app | source='learned': auto-promoted from confirmations
CREATE TABLE IF NOT EXISTS imp_filename_pattern (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern         VARCHAR(120) NOT NULL,
    doc_type        VARCHAR(50)  NOT NULL,
    base_confidence NUMERIC(3,2) NOT NULL DEFAULT 0.75,
    confirmed_count INTEGER      NOT NULL DEFAULT 0,
    failed_count    INTEGER      NOT NULL DEFAULT 0,
    source          VARCHAR(20)  NOT NULL DEFAULT 'seed',
    active          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (pattern, doc_type)
);
CREATE INDEX IF NOT EXISTS imp_filename_pattern_active_idx
    ON imp_filename_pattern (active, doc_type);

-- --- imp_header_doc_type ----------------------------------------------------
-- Learned mapping: set of canonical fields found in a document -> doc_type
-- Purely learned (no seeds): starts empty, filled by confirmations
CREATE TABLE IF NOT EXISTS imp_header_doc_type (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_fields_hash VARCHAR(64) NOT NULL UNIQUE,
    canonical_fields      TEXT[]      NOT NULL,
    doc_type              VARCHAR(50) NOT NULL,
    confirmed_count       INTEGER     NOT NULL DEFAULT 0,
    failed_count          INTEGER     NOT NULL DEFAULT 0,
    active                BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS imp_header_doc_type_active_idx
    ON imp_header_doc_type (doc_type) WHERE active = TRUE;

-- --- imp_field_alias learning columns ---------------------------------------
-- source='seed': from migrations | source='learned': auto from confirmed column mappings
ALTER TABLE imp_field_alias
    ADD COLUMN IF NOT EXISTS source          VARCHAR(20)  NOT NULL DEFAULT 'seed',
    ADD COLUMN IF NOT EXISTS confirmed_count INTEGER      NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_seen_at    TIMESTAMPTZ;

-- Partial unique index so NULL tenant_id upserts work correctly
CREATE UNIQUE INDEX IF NOT EXISTS imp_field_alias_global_uq
    ON imp_field_alias (canonical_field, alias)
    WHERE tenant_id IS NULL;

-- --- Pre-classifier thresholds (sector_field_defaults) ----------------------
INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, ord, label, options)
VALUES
    (gen_random_uuid(), '_system', 'importador.pre_classifier', 'min_header_confirmations',    TRUE, FALSE, 1, 'Min confirmations for header->doctype trust',  '[2]'::jsonb),
    (gen_random_uuid(), '_system', 'importador.pre_classifier', 'filename_min_confidence',     TRUE, FALSE, 2, 'Min filename pattern confidence to skip AI',   '[0.70]'::jsonb),
    (gen_random_uuid(), '_system', 'importador.pre_classifier', 'header_coverage_min_ratio',   TRUE, FALSE, 3, 'Min ratio of headers matching canonical fields','[0.50]'::jsonb),
    (gen_random_uuid(), '_system', 'importador.pre_classifier', 'structured_skip_threshold',   TRUE, FALSE, 4, 'Min confidence to skip AI on structured docs',  '[0.75]'::jsonb),
    (gen_random_uuid(), '_system', 'importador.pre_classifier', 'ocr_weird_ratio_max',         TRUE, FALSE, 5, 'Max weird-char ratio before forcing vision',    '[0.15]'::jsonb)
ON CONFLICT DO NOTHING;

-- --- Seeds for imp_filename_pattern -----------------------------------------
-- Based on real-world file naming conventions - editable/extendable from DB
INSERT INTO imp_filename_pattern (pattern, doc_type, base_confidence, source) VALUES
    ('nomi.?na|nomina|planilla',                    'PAYROLL',        0.80, 'seed'),
    ('ticket|tiken|recibo|receipt|boleta',          'RECEIPT',        0.75, 'seed'),
    ('stock|existencia|inventari',                  'INVENTORY',      0.75, 'seed'),
    ('costeo|receta|costing',                       'COSTING',        0.75, 'seed'),
    ('catalog|catalogo|price.?list|lista.?preci',   'PRICE_LIST',     0.75, 'seed'),
    ('movimientos|extracto|estado.?cuenta',         'BANK_STATEMENT', 0.75, 'seed'),
    ('ventas|sales|reporte.?venta',                 'SALES',          0.70, 'seed'),
    ('factura|invoice',                             'INVOICE',        0.75, 'seed'),
    ('gastos|expenses',                             'EXPENSES',       0.70, 'seed'),
    ('payroll',                                     'PAYROLL',        0.80, 'seed')
ON CONFLICT (pattern, doc_type) DO NOTHING;

COMMIT;
