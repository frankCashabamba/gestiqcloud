-- Recrear tabla payments alineada con el modelo ORM (finance/payment.py).
--
-- La tabla legacy tenía 7 columnas (bank_tx_id, invoice_id, date, applied_amount, notes)
-- pero el modelo fue rediseñado con un esquema completo de pagos.
-- La tabla está vacía (0 filas), así que es seguro hacer DROP + CREATE.

BEGIN;

-- Crear enums si no existen
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_status') THEN
        CREATE TYPE payment_status AS ENUM (
            'PENDING', 'IN_PROGRESS', 'CONFIRMED', 'FAILED', 'CANCELLED'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'payment_method') THEN
        CREATE TYPE payment_method AS ENUM (
            'CASH', 'BANK_TRANSFER', 'CARD', 'CHEQUE', 'DIRECT_DEBIT', 'OTHER'
        );
    END IF;
END$$;

-- Guardar y eliminar la tabla legacy
DROP TABLE IF EXISTS payments;

-- Crear tabla con el esquema del modelo ORM
CREATE TABLE payments (
    -- BaseTransactionalModel fields
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID            NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),

    -- Amount & currency
    amount          NUMERIC(14,2)   NOT NULL,
    currency        VARCHAR(3)      NOT NULL DEFAULT 'EUR',

    -- Dates
    payment_date    DATE            NOT NULL,
    scheduled_date  DATE,
    confirmed_date  DATE,

    -- Method & status
    method          payment_method  NOT NULL DEFAULT 'BANK_TRANSFER',
    status          payment_status  NOT NULL DEFAULT 'PENDING',

    -- Document reference
    ref_doc_type    VARCHAR(50)     NOT NULL,
    ref_doc_id      UUID            NOT NULL,

    -- Bank account (FK to chart_of_accounts)
    bank_account_id UUID            REFERENCES chart_of_accounts(id) ON DELETE SET NULL,

    -- Description & notes
    description     VARCHAR(255),
    notes           TEXT,

    -- Retry tracking
    retry_count     INTEGER         NOT NULL DEFAULT 0,
    last_error      VARCHAR(500),

    -- Bank reference
    bank_reference  VARCHAR(100),

    -- Audit
    created_by      UUID,
    confirmed_by    UUID
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_payments_tenant_id    ON payments (tenant_id);
CREATE INDEX IF NOT EXISTS idx_payments_status       ON payments (status);
CREATE INDEX IF NOT EXISTS idx_payments_payment_date ON payments (payment_date);
CREATE INDEX IF NOT EXISTS idx_payments_ref_doc_id   ON payments (ref_doc_id);

COMMIT;
