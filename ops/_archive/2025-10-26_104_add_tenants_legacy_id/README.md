Title: Add legacy tenant_id (int) mapping to tenants

Summary
- Adds column tenants.tenant_id (INTEGER, UNIQUE) used by admin endpoints
  to map legacy integer IDs to the UUID primary key.
- Creates a unique index to support ON CONFLICT (tenant_id).

Notes
- We do not add a foreign key to core_empresa because the modern schema
  does not include that table in the baseline. The column is a lightweight
  compatibility bridge for existing code paths.

