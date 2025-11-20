-- =====================================================
-- AI INCIDENT TABLES: Incidents, Notifications
-- Migration: 2025-11-01_150_ai_incident_tables
-- =====================================================

BEGIN;

-- =====================================================
-- INCIDENTS: System Incidents and Alerts
-- =====================================================
CREATE TABLE IF NOT EXISTS incidents (
    id UUID DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    severidad VARCHAR(20) NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    descripcion TEXT,
    stack_trace TEXT,
    context JSONB,
    estado VARCHAR(20) NOT NULL DEFAULT 'open',
    assigned_to UUID,
    auto_detected BOOLEAN NOT NULL DEFAULT false,
    auto_resolved BOOLEAN NOT NULL DEFAULT false,
    ia_analysis JSONB,
    ia_suggestion TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_incidents_tenant_estado ON incidents(tenant_id, estado);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at);
CREATE INDEX IF NOT EXISTS idx_incidents_severidad ON incidents(severidad);

-- =====================================================
-- NOTIFICATION_CHANNELS: Notification Delivery Channels
-- =====================================================
CREATE TABLE IF NOT EXISTS notification_channels (
    id UUID DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    config JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_notification_channels_tenant ON notification_channels(tenant_id);

-- =====================================================
-- NOTIFICATION_LOG: Notification Delivery Log
-- =====================================================
CREATE TABLE IF NOT EXISTS notification_log (
    id UUID DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    channel_id UUID,
    incident_id UUID,
    stock_alert_id UUID,
    tipo VARCHAR(50) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(255),
    body TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    extra_data JSONB,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES notification_channels(id) ON DELETE SET NULL,
    FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
    FOREIGN KEY (stock_alert_id) REFERENCES stock_alerts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_notification_log_tenant ON notification_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_notification_log_status ON notification_log(status);
CREATE INDEX IF NOT EXISTS idx_notification_log_sent_at ON notification_log(sent_at);

COMMIT;
