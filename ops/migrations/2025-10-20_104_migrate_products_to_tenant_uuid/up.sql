-- Migrate products to tenant_id UUID (drop empresa_id)

-- Drop all existing RLS policies first
DROP POLICY IF EXISTS tenant_isolation ON products;
DROP POLICY IF EXISTS tenant_isolation_products ON products;
DROP POLICY IF EXISTS tenant_insert_products ON products;
DROP POLICY IF EXISTS tenant_update_products ON products;
DROP POLICY IF EXISTS tenant_delete_products ON products;

-- Disable RLS temporarily
ALTER TABLE products DISABLE ROW LEVEL SECURITY;

-- Drop old index if exists
DROP INDEX IF EXISTS ix_products_empresa_id;

-- Drop foreign key to empresa_id
ALTER TABLE products DROP CONSTRAINT IF EXISTS fk_products_empresa;
ALTER TABLE products DROP CONSTRAINT IF EXISTS products_empresa_id_fkey;

-- Drop empresa_id column
ALTER TABLE products DROP COLUMN IF EXISTS empresa_id;

-- Enable RLS and create new policy using tenant_id
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON products
  USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- Ensure tenant_id index exists (from previous migration)
CREATE INDEX IF NOT EXISTS ix_products_tenant_id ON products (tenant_id);
