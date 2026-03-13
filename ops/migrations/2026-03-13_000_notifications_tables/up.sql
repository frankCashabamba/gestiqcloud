-- Migration: notifications tables (unified system)
-- Adds notifications (in-app) and notification_templates tables.
-- notification_channels and notification_logs already exist in the base schema.

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    channel VARCHAR(20) NOT NULL,             -- email, sms, push, in_app, webhook
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',  -- low, medium, high, urgent
    status VARCHAR(20) NOT NULL DEFAULT 'pending',   -- pending, sent, failed, read, archived
    metadata JSONB,
    read_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_tenant_user
    ON notifications(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_status
    ON notifications(status)
    WHERE archived_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_notifications_created_at
    ON notifications(created_at DESC);

-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    subject_template VARCHAR(500) NOT NULL,
    body_template TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_notification_template_tenant_name UNIQUE (tenant_id, name)
);

CREATE INDEX IF NOT EXISTS idx_notification_templates_tenant
    ON notification_templates(tenant_id);
