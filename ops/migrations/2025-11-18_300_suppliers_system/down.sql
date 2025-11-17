-- Rollback: 2025-11-18_300_suppliers_system

BEGIN;

DROP TRIGGER IF EXISTS supplier_addresses_updated_at ON supplier_addresses;
DROP TRIGGER IF EXISTS supplier_contacts_updated_at ON supplier_contacts;
DROP TRIGGER IF EXISTS suppliers_updated_at ON suppliers;

DROP POLICY IF EXISTS tenant_isolation_suppliers ON suppliers;

DROP TABLE IF EXISTS supplier_addresses CASCADE;
DROP TABLE IF EXISTS supplier_contacts CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;

DROP FUNCTION IF EXISTS update_updated_at_column();

COMMIT;
