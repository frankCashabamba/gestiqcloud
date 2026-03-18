-- Migration: 2026-03-17_002_copilot_conversations
-- Creates tables for persisting copilot chat history.
-- Idempotente.

CREATE TABLE IF NOT EXISTS copilot_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id UUID NOT NULL,
    title VARCHAR(200),
    current_module VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_copilot_conv_tenant_user') THEN
        CREATE INDEX ix_copilot_conv_tenant_user ON copilot_conversations(tenant_id, user_id);
    END IF;
END $$;

ALTER TABLE copilot_conversations ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'copilot_conversations_tenant_isolation') THEN
        CREATE POLICY copilot_conversations_tenant_isolation ON copilot_conversations
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS copilot_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES copilot_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_copilot_messages_conversation') THEN
        CREATE INDEX ix_copilot_messages_conversation ON copilot_messages(conversation_id);
    END IF;
END $$;
