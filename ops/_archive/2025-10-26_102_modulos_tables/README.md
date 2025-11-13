Title: Create modulos tables for Admin module

Summary
- Adds core tables used by the Admin "módulos" feature:
  - modulos_modulo (catalog of modules; no RLS)
  - modulos_empresamodulo (module activation per tenant)
  - modulos_moduloasignado (module assignment per user/tenant)

Notes
- This aligns with SQLAlchemy models in apps/backend/app/models/core/modulo.py
- Uses UUID tenant_id (references tenants.id)
- Leaves modulos_modulo without RLS (admin-only) and enables RLS on assignment table if needed in future.

