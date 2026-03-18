-- Rollback: 2026-03-17_001_branches
ALTER TABLE company_user_roles DROP COLUMN IF EXISTS branch_id;
ALTER TABLE pos_shifts DROP COLUMN IF EXISTS branch_id;
ALTER TABLE pos_registers DROP COLUMN IF EXISTS branch_id;
ALTER TABLE warehouses DROP COLUMN IF EXISTS branch_id;
DROP TABLE IF EXISTS branches;
