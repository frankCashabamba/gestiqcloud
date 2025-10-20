CREATE TABLE einv_credentials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  country CHAR(2) NOT NULL, -- ES/EC
  certificate_type TEXT NOT NULL, -- 'p12', 'pfx'
  certificate_content BYTEA NOT NULL, -- Base64 encoded certificate
  password TEXT NOT NULL,
  expires_at DATE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(tenant_id, country, certificate_type)
);

-- RLS Policy
ALTER TABLE einv_credentials ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_einv_credentials ON einv_credentials
  USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- Index for faster lookups
CREATE INDEX idx_einv_credentials_tenant_country ON einv_credentials (tenant_id, country);
