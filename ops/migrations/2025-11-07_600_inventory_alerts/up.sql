-- =====================================================
-- INVENTORY: Alerts Configuration Table
-- =====================================================
-- Table to configure inventory alerts for low stock notifications
-- Supports multiple channels: email, WhatsApp, Telegram

CREATE TABLE IF NOT EXISTS inventory_alert_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    alert_type VARCHAR(50) NOT NULL DEFAULT 'low_stock', -- low_stock, out_of_stock, etc.
    threshold_type VARCHAR(20) NOT NULL DEFAULT 'fixed', -- fixed, percentage
    threshold_value NUMERIC(10, 2), -- fixed quantity or percentage
    warehouse_ids UUID[] DEFAULT '{}', -- empty array means all warehouses
    category_ids UUID[] DEFAULT '{}', -- empty array means all categories
    product_ids UUID[] DEFAULT '{}', -- empty array means all products

    -- Notification channels
    notify_email BOOLEAN DEFAULT FALSE,
    email_recipients TEXT[] DEFAULT '{}',
    notify_whatsapp BOOLEAN DEFAULT FALSE,
    whatsapp_numbers TEXT[] DEFAULT '{}',
    notify_telegram BOOLEAN DEFAULT FALSE,
    telegram_chat_ids TEXT[] DEFAULT '{}',

    -- Schedule
    check_frequency_minutes INTEGER DEFAULT 60, -- how often to check
    last_checked_at TIMESTAMPTZ,
    next_check_at TIMESTAMPTZ,

    -- Settings
    cooldown_hours INTEGER DEFAULT 24, -- don't send same alert within hours
    max_alerts_per_day INTEGER DEFAULT 10,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inventory_alert_configs_tenant ON inventory_alert_configs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_inventory_alert_configs_active ON inventory_alert_configs(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_inventory_alert_configs_next_check ON inventory_alert_configs(next_check_at) WHERE is_active = TRUE;

-- RLS for inventory_alert_configs
ALTER TABLE inventory_alert_configs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_inventory_alert_configs ON inventory_alert_configs;
CREATE POLICY tenant_isolation_inventory_alert_configs ON inventory_alert_configs
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- =====================================================
-- INVENTORY: Alert History Table
-- =====================================================
-- Table to track sent alerts and prevent duplicates

CREATE TABLE IF NOT EXISTS inventory_alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    alert_config_id UUID NOT NULL REFERENCES inventory_alert_configs(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id UUID REFERENCES warehouses(id) ON DELETE SET NULL,
    alert_type VARCHAR(50) NOT NULL,
    threshold_value NUMERIC(10, 2),
    current_stock NUMERIC(10, 2),
    message TEXT,
    channels_sent TEXT[] DEFAULT '{}', -- email, whatsapp, telegram
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inventory_alert_history_tenant ON inventory_alert_history(tenant_id);
CREATE INDEX IF NOT EXISTS idx_inventory_alert_history_config ON inventory_alert_history(alert_config_id);
CREATE INDEX IF NOT EXISTS idx_inventory_alert_history_product ON inventory_alert_history(product_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_alert_history_cooldown ON inventory_alert_history(tenant_id, product_id, alert_type, sent_at DESC);

-- RLS for inventory_alert_history
ALTER TABLE inventory_alert_history ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_inventory_alert_history ON inventory_alert_history;
CREATE POLICY tenant_isolation_inventory_alert_history ON inventory_alert_history
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));
