BEGIN;

CREATE TABLE IF NOT EXISTS tenant_field_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  module TEXT NOT NULL,
  field TEXT NOT NULL,
  visible BOOLEAN DEFAULT TRUE,
  required BOOLEAN DEFAULT FALSE,
  ord SMALLINT,
  label TEXT,
  help TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(tenant_id, module, field)
);

CREATE INDEX IF NOT EXISTS idx_tfc_tenant ON tenant_field_config(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tfc_tenant_module ON tenant_field_config(tenant_id, module);

COMMIT;

