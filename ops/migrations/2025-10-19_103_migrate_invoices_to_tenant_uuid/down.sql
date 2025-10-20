-- Reverse migration: Revert facturas to empresa_id int from tenant_id UUID

-- Drop RLS policy and disable RLS
DROP POLICY IF EXISTS tenant_isolation ON facturas;
ALTER TABLE facturas DISABLE ROW LEVEL SECURITY;

-- Drop index
DROP INDEX IF EXISTS idx_facturas_tenant_id;

-- Add back empresa_id column
ALTER TABLE facturas ADD COLUMN empresa_id INTEGER;

-- Backfill empresa_id using existing tenant_id and the tenants table
UPDATE facturas f
SET empresa_id = t.empresa_id
FROM tenants t
WHERE f.tenant_id = t.id;

-- Set empresa_id as NOT NULL and add foreign key constraint
ALTER TABLE facturas ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE facturas ADD CONSTRAINT fk_facturas_empresa_id FOREIGN KEY (empresa_id) REFERENCES core_empresa(id);

-- Drop tenant_id column
ALTER TABLE facturas DROP COLUMN tenant_id;

-- Recreate RLS policy to use empresa_id (legacy)
ALTER TABLE facturas ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON facturas
  USING (empresa_id::text = current_setting('app.tenant_id', TRUE));
