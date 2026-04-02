BEGIN;

-- Allow global/system audit rows (tenant_id IS NULL) while preserving tenant isolation.
DROP POLICY IF EXISTS tenant_isolation_policy ON public.audit_events;

CREATE POLICY tenant_isolation_policy ON public.audit_events
    USING (
        tenant_id IS NULL
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
    )
    WITH CHECK (
        tenant_id IS NULL
        OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
    );

COMMIT;
