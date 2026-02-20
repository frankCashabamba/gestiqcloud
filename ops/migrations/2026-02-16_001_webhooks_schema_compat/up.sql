-- Webhooks schema compatibility migration.
-- Ensures both legacy SQL flow and new ORM flow can coexist.

CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    event_type VARCHAR(50),
    target_url VARCHAR(2048),
    secret VARCHAR(255) NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    retry_count INTEGER NOT NULL DEFAULT 5,
    timeout_seconds INTEGER NOT NULL DEFAULT 30,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    last_delivery_at TIMESTAMP WITHOUT TIME ZONE,
    -- Legacy compatibility columns
    event VARCHAR(50),
    url VARCHAR(2048),
    active BOOLEAN NOT NULL DEFAULT TRUE
);

ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS tenant_id UUID;
ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS event_type VARCHAR(50);
ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS target_url VARCHAR(2048);
ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS secret VARCHAR(255);
ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 5;
ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS timeout_seconds INTEGER NOT NULL DEFAULT 30;
ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW();
ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW();
ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS last_delivery_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS event VARCHAR(50);
ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS url VARCHAR(2048);
ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;

UPDATE webhook_subscriptions
SET
    event_type = COALESCE(event_type, event),
    event = COALESCE(event, event_type),
    target_url = COALESCE(target_url, url),
    url = COALESCE(url, target_url),
    is_active = COALESCE(is_active, active, TRUE),
    active = COALESCE(active, is_active, TRUE),
    updated_at = COALESCE(updated_at, NOW())
WHERE
    event_type IS NULL
    OR event IS NULL
    OR target_url IS NULL
    OR url IS NULL
    OR is_active IS NULL
    OR active IS NULL
    OR updated_at IS NULL;

CREATE OR REPLACE FUNCTION sync_webhook_subscriptions_columns()
RETURNS TRIGGER AS $$
BEGIN
    NEW.event_type := COALESCE(NEW.event_type, NEW.event);
    NEW.event := COALESCE(NEW.event, NEW.event_type);
    NEW.target_url := COALESCE(NEW.target_url, NEW.url);
    NEW.url := COALESCE(NEW.url, NEW.target_url);
    NEW.is_active := COALESCE(NEW.is_active, NEW.active, TRUE);
    NEW.active := COALESCE(NEW.active, NEW.is_active, TRUE);
    NEW.updated_at := COALESCE(NEW.updated_at, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_webhook_subscriptions_columns ON webhook_subscriptions;
CREATE TRIGGER trg_sync_webhook_subscriptions_columns
BEFORE INSERT OR UPDATE ON webhook_subscriptions
FOR EACH ROW
EXECUTE FUNCTION sync_webhook_subscriptions_columns();

CREATE INDEX IF NOT EXISTS ix_webhook_subscriptions_tenant_id ON webhook_subscriptions (tenant_id);
CREATE INDEX IF NOT EXISTS ix_webhook_subscriptions_event_type ON webhook_subscriptions (event_type);
CREATE INDEX IF NOT EXISTS ix_webhook_subscriptions_event ON webhook_subscriptions (event);
CREATE INDEX IF NOT EXISTS ix_webhook_subscriptions_is_active ON webhook_subscriptions (is_active);
CREATE INDEX IF NOT EXISTS ix_webhook_subscriptions_active ON webhook_subscriptions (active);


CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- New ORM flow columns
    subscription_id UUID REFERENCES webhook_subscriptions(id) ON DELETE CASCADE,
    event_type VARCHAR(50),
    status_code INTEGER,
    response_body TEXT,
    error_message VARCHAR(1024),
    attempt_number INTEGER NOT NULL DEFAULT 1,
    next_retry_at TIMESTAMP WITHOUT TIME ZONE,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    -- Legacy flow columns
    tenant_id UUID,
    event VARCHAR(100),
    target_url VARCHAR(2048),
    secret VARCHAR(255),
    status VARCHAR(20) DEFAULT 'PENDING',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    -- Shared
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS subscription_id UUID;
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS event_type VARCHAR(50);
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS status_code INTEGER;
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS response_body TEXT;
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS error_message VARCHAR(1024);
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS attempt_number INTEGER NOT NULL DEFAULT 1;
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS tenant_id UUID;
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS event VARCHAR(100);
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS target_url VARCHAR(2048);
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS secret VARCHAR(255);
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'PENDING';
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS last_error TEXT;
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS payload JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW();
ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_webhook_deliveries_subscription_id'
    ) THEN
        ALTER TABLE webhook_deliveries
        ADD CONSTRAINT fk_webhook_deliveries_subscription_id
        FOREIGN KEY (subscription_id)
        REFERENCES webhook_subscriptions(id)
        ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_webhook_deliveries_subscription_id ON webhook_deliveries (subscription_id);
CREATE INDEX IF NOT EXISTS ix_webhook_deliveries_event_type ON webhook_deliveries (event_type);
CREATE INDEX IF NOT EXISTS ix_webhook_deliveries_event ON webhook_deliveries (event);
CREATE INDEX IF NOT EXISTS ix_webhook_deliveries_next_retry_at ON webhook_deliveries (next_retry_at);
CREATE INDEX IF NOT EXISTS ix_webhook_deliveries_created_at ON webhook_deliveries (created_at);
CREATE INDEX IF NOT EXISTS ix_webhook_deliveries_status ON webhook_deliveries (status);
