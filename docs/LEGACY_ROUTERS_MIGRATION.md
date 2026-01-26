# Legacy Routers Migration

**Status:** ✅ Completed  
**Date:** 2026-01-17

---

## Summary

All 23 legacy routers from `apps/backend/app/routers/` have been migrated to the modern DDD-style modular pattern in `apps/backend/app/modules/*/interface/http/`.

The original router files are now **compatibility shims** that re-export from the new locations, ensuring backward compatibility.

---

## Migration Map

### New Modules Created

| Module | Purpose |
|--------|---------|
| `modules/notifications/` | Notification channels, logs, alerts |
| `modules/onboarding/` | Tenant initialization |
| `modules/analytics/` | Dashboard KPIs and stats |
| `modules/support/` | Incidents and alerts |
| `modules/shared/` | General listings, home |

### Router Migrations

| Original Router | New Location | Status |
|-----------------|--------------|--------|
| `routers/notifications.py` | `modules/notifications/interface/http/tenant.py` | ✅ Shim |
| `routers/onboarding_init.py` | `modules/onboarding/interface/http/tenant.py` | ✅ Shim |
| `routers/initial_config.py` | `modules/onboarding/interface/http/initial_config.py` | ✅ Shim |
| `routers/dashboard_kpis.py` | `modules/analytics/interface/http/tenant.py` | ✅ Shim |
| `routers/dashboard_stats.py` | `modules/analytics/interface/http/tenant.py` | ✅ Shim |
| `routers/admin_stats.py` | `modules/analytics/interface/http/admin.py` | ✅ Shim |
| `routers/roles.py` | `modules/identity/interface/http/roles.py` | ✅ Shim |
| `routers/protected.py` | `modules/identity/interface/http/protected.py` | ✅ Shim |
| `routers/sectors.py` | `modules/admin_config/interface/http/sectors.py` | ✅ Shim |
| `routers/admin_sector_config.py` | `modules/admin_config/interface/http/sector_config.py` | ✅ Shim |
| `routers/sector_plantillas.py` | `modules/admin_config/interface/http/sector_plantillas.py` | ✅ Shim |
| `routers/business_categories.py` | `modules/admin_config/interface/http/business_categories.py` | ✅ Shim |
| `routers/admin_scripts.py` | `modules/admin_config/interface/http/scripts.py` | ✅ Shim |
| `routers/migrations.py` | `modules/admin_config/interface/http/migrations.py` | ✅ Shim |
| `routers/company_settings.py` | `modules/settings/interface/http/company.py` | ✅ Shim |
| `routers/company_settings_public.py` | `modules/settings/interface/http/public.py` | ✅ Shim |
| `routers/settings_router.py` | `modules/settings/interface/http/settings_router.py` | ✅ Shim |
| `routers/categories.py` | `modules/products/interface/http/categories.py` | ✅ Shim |
| `routers/payments.py` | `modules/reconciliation/interface/http/payments.py` | ✅ Shim |
| `routers/general_listings.py` | `modules/shared/interface/http/listings.py` | ✅ Shim |
| `routers/home.py` | `modules/shared/interface/http/home.py` | ✅ Shim |
| `routers/incidents.py` | `modules/support/interface/http/incidents.py` | ✅ Shim |
| `routers/router_admins.py` | `modules/users/interface/http/router_admins.py` | ✅ Shim |
| `routers/admin/usuarios.py` | `modules/users/interface/http/admin_usuarios.py` | ✅ Shim |
| `routers/tenant/roles.py` | `modules/identity/interface/http/tenant_roles.py` | ✅ Shim |
| `routers/tenant/usuarios.py` | `modules/users/interface/http/tenant_usuarios.py` | ✅ Shim |

---

## Shim Pattern

All legacy routers now follow this pattern:

```python
"""Compatibility shim: re-export router from modular location."""
from app.modules.{module}.interface.http.{file} import router

__all__ = ["router"]
```

This ensures:
- **Backward compatibility**: Existing imports continue to work
- **Gradual deprecation**: Can add deprecation warnings later
- **Clean transition**: New code imports from `modules/`

---

## Additional Changes

### Translations
All Spanish text in the migrated routers was translated to English:
- Error messages
- Docstrings
- Comments
- Function names (where appropriate)

### Dependencies Updated
- `platform/http/router.py` updated to mount from new module locations
- Fallback to shims for resilience

---

## Future Work

1. **Deprecation warnings**: Add logging when shims are used
2. **Remove shims**: After 6-month sunset period (target: July 2026)
3. **Update imports**: Gradually update all internal imports to use `modules/` paths
