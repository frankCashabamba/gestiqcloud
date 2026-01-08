-- Migration: 2025-12-18_000_assign_next_number
-- Description: Create doc_number_counters table and assign_next_number function.

BEGIN;

CREATE TABLE IF NOT EXISTS doc_number_counters (
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    doc_type VARCHAR NOT NULL,
    year INTEGER NOT NULL,
    series VARCHAR NOT NULL DEFAULT 'A',
    current_no INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (tenant_id, doc_type, year, series)
);

CREATE OR REPLACE FUNCTION public.current_tenant()
RETURNS UUID
LANGUAGE sql
AS $$
SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION public.assign_next_number(
    p_tenant UUID,
    p_tipo TEXT,
    p_anio INTEGER,
    p_serie TEXT
) RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    next_no INTEGER;
BEGIN
    INSERT INTO doc_number_counters (
        tenant_id,
        doc_type,
        year,
        series,
        current_no,
        created_at,
        updated_at
    )
    VALUES (
        p_tenant,
        p_tipo,
        p_anio,
        COALESCE(p_serie, 'A'),
        1,
        now(),
        now()
    )
    ON CONFLICT (tenant_id, doc_type, year, series)
    DO UPDATE SET
        current_no = doc_number_counters.current_no + 1,
        updated_at = now()
    RETURNING current_no INTO next_no;

    RETURN next_no;
END;
$$;

COMMIT;
