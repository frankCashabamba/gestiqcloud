-- Reverse migration: Revert products to empresa_id int from tenant_id UUID

-- Drop RLS policy and disable RLS
DROP POLICY IF EXISTS tenant_isolation ON products;
ALTER TABLE products DISABLE ROW LEVEL SECURITY;

-- Drop tenant_id index
DROP INDEX IF EXISTS ix_products_tenant_id;

-- Add back empresa_id column
ALTER TABLE products ADD COLUMN empresa_id INTEGER;

-- Backfill empresa_id using existing tenant_id and the tenants table
UPDATE products p
SET empresa_id = t.empresa_id
FROM tenants t
WHERE p.tenant_id = t.id;

-- Set empresa_id as NOT NULL and add foreign key constraint
ALTER TABLE products ALTER COLUMN empresa_id SET NOT NULL;
ALTER TABLE products ADD CONSTRAINT fk_products_empresa FOREIGN KEY (empresa_id) REFERENCES core_empresa(id);

-- Enable RLS and recreate old policy using empresa_id
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON products
  USING (empresa_id::text = current_setting('app.tenant_id', TRUE));

-- Create index on empresa_id
CREATE INDEX ix_products_empresa_id ON products (empresa_id);
