-- Reverse webhooks schema compatibility migration.
-- Drop indexes, trigger, function, and tables.

DROP INDEX IF EXISTS ix_webhook_deliveries_status;
DROP INDEX IF EXISTS ix_webhook_deliveries_created_at;
DROP INDEX IF EXISTS ix_webhook_deliveries_next_retry_at;
DROP INDEX IF EXISTS ix_webhook_deliveries_event;
DROP INDEX IF EXISTS ix_webhook_deliveries_event_type;
DROP INDEX IF EXISTS ix_webhook_deliveries_subscription_id;
DROP TABLE IF EXISTS webhook_deliveries;

DROP TRIGGER IF EXISTS trg_sync_webhook_subscriptions_columns ON webhook_subscriptions;
DROP FUNCTION IF EXISTS sync_webhook_subscriptions_columns();

DROP INDEX IF EXISTS ix_webhook_subscriptions_active;
DROP INDEX IF EXISTS ix_webhook_subscriptions_is_active;
DROP INDEX IF EXISTS ix_webhook_subscriptions_event;
DROP INDEX IF EXISTS ix_webhook_subscriptions_event_type;
DROP INDEX IF EXISTS ix_webhook_subscriptions_tenant_id;
DROP TABLE IF EXISTS webhook_subscriptions;
