DROP INDEX IF EXISTS uq_pos_receipts_tenant_client_request_id;

ALTER TABLE pos_receipts
    DROP COLUMN IF EXISTS client_request_id;
