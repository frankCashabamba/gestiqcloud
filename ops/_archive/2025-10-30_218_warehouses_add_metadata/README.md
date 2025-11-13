Title: Add metadata column to warehouses

Summary
- Adds JSONB column `metadata` to `warehouses` to match the SQLAlchemy model mapping `extra_metadata -> "metadata"`.

Why
- Current model selects `warehouses.metadata`, but the column is missing causing runtime errors when listing warehouses.

Up
- ALTER TABLE warehouses ADD COLUMN metadata JSONB;

Down
- ALTER TABLE warehouses DROP COLUMN IF EXISTS metadata;
