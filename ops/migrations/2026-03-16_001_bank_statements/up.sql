-- Migration: 2026-03-16_001_bank_statements
-- Creates bank_statements and statement_lines tables for the reconciliation module.
-- Idempotente: usa IF NOT EXISTS en todas las operaciones.

-- ============================================================
-- 1. bank_statements
-- ============================================================
CREATE TABLE IF NOT EXISTS public.bank_statements (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    bank_name       VARCHAR(200) NOT NULL,
    account_number  VARCHAR(50)  NOT NULL,
    statement_date  DATE         NOT NULL,
    file_name       VARCHAR(255),
    import_format   VARCHAR(20)  NOT NULL DEFAULT 'manual',
    status          VARCHAR(20)  NOT NULL DEFAULT 'imported',
    total_transactions INTEGER   NOT NULL DEFAULT 0,
    matched_count      INTEGER   NOT NULL DEFAULT 0,
    unmatched_count    INTEGER   NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bank_statements_tenant_id
    ON public.bank_statements(tenant_id);

CREATE INDEX IF NOT EXISTS idx_bank_statements_statement_date
    ON public.bank_statements(statement_date);

-- ============================================================
-- 2. statement_lines
-- ============================================================
CREATE TABLE IF NOT EXISTS public.statement_lines (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    statement_id        UUID         NOT NULL REFERENCES public.bank_statements(id) ON DELETE CASCADE,
    tenant_id           UUID         NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    transaction_date    DATE         NOT NULL,
    description         VARCHAR(500) NOT NULL,
    reference           VARCHAR(200),
    amount              NUMERIC(15,2) NOT NULL,
    balance             NUMERIC(15,2),
    transaction_type    VARCHAR(20)  NOT NULL,
    matched_invoice_id  UUID,
    match_status        VARCHAR(20)  NOT NULL DEFAULT 'unmatched',
    match_confidence    NUMERIC(5,2),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_statement_lines_statement_id
    ON public.statement_lines(statement_id);

CREATE INDEX IF NOT EXISTS idx_statement_lines_tenant_id
    ON public.statement_lines(tenant_id);

-- ============================================================
-- 3. RLS
-- ============================================================
ALTER TABLE public.bank_statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bank_statements FORCE ROW LEVEL SECURITY;

ALTER TABLE public.statement_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.statement_lines FORCE ROW LEVEL SECURITY;

-- tenant isolation policy
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'bank_statements'
          AND policyname = 'tenant_isolation'
    ) THEN
        CREATE POLICY tenant_isolation ON public.bank_statements
            USING (tenant_id::text = current_setting('app.tenant_id', true));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'statement_lines'
          AND policyname = 'tenant_isolation'
    ) THEN
        CREATE POLICY tenant_isolation ON public.statement_lines
            USING (tenant_id::text = current_setting('app.tenant_id', true));
    END IF;
END$$;

-- admin bypass policy (consistent with 2026-03-16_000_rls_admin_bypass)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'bank_statements'
          AND policyname = 'admin_bypass'
    ) THEN
        CREATE POLICY admin_bypass ON public.bank_statements
            USING (public.is_app_admin());
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename  = 'statement_lines'
          AND policyname = 'admin_bypass'
    ) THEN
        CREATE POLICY admin_bypass ON public.statement_lines
            USING (public.is_app_admin());
    END IF;
END$$;
