ALTER TABLE pos_receipts
    ADD COLUMN IF NOT EXISTS client_request_id VARCHAR(120);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pos_receipts_tenant_client_request_id
    ON pos_receipts (tenant_id, client_request_id)
    WHERE client_request_id IS NOT NULL;
