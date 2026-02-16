# Module Normalization to English - Complete Summary

## Problem
The GestiqCloud application had duplicate modules in the navigation menu due to having both Spanish and English versions of the same modules:
- **"Compras"** (Spanish, old) and **"purchases"** (English, new)
- **"Ventas"** (Spanish, old) and **"sales"** (English, new)
- **"Facturacion"** (Spanish, old) and **"billing"** (English, new)

This resulted in the menu showing duplicate entries like "Compras" appearing twice.

## Root Cause
1. **Legacy Spanish modules** were created in the database without URLs
2. **New English modules** with proper URLs were added to support internationalization
3. The **module detection system** (`registrarModulosFS`) would read folder names from the filesystem and create modules without normalization, leading to duplicates
4. The **frontend translation system** would map both Spanish and English module names to the same Spanish translation, causing visible duplicates

## Solution Implemented

### 1. Database Normalization (SQL Migration)
**File**: `ops/migrations/2026-02-14_005_normalize_modules_to_english/up.sql`

Actions:
- **Deactivated** old Spanish modules: Compras, Ventas, Facturacion
- **Renamed** remaining Spanish module names to English:
  - `reportes` → `reports`
  - `usuarios` → `users`
  - `produccion` → `manufacturing`

Result: **23 active modules, all with English names**

### 2. Backend Module Registration Normalization
**File**: `apps/backend/app/modules/modules_catalog/interface/http/admin.py`

Added `_normalize_module_name()` function that maps Spanish folder names to English:
```python
{
    "compras": "purchases",
    "ventas": "sales",
    "facturacion": "billing",
    "reportes": "reports",
    "usuarios": "users",
    "produccion": "manufacturing",
    "clientes": "customers",
    "proveedores": "suppliers",
    "inventario": "inventory",
    "gastos": "expenses",
    "finanzas": "finances",
    "contabilidad": "accounting",
}
```

This ensures that when folders are scanned via "Detectar desde FS", they are normalized to English names.

### 3. Backend Filter for Active Modules
**File**: `apps/backend/app/modules/modules_catalog/infrastructure/repositories.py`

Modified `list_asignados()` to only return active modules:
```python
return [self._to_dto(ma.module) for ma in rows if ma.module and ma.module.active]
```

This ensures that inactive (deprecated) modules don't appear in the frontend menu.

### 4. Frontend Translation Completion
**File**: `apps/tenant/src/i18n/locales/es.json`

Added missing module translations in the `modules` section:
```json
{
  "modules": {
    "accounting": "Contabilidad",
    "billing": "Facturación",
    "copilot": "Copilot",
    "crm": "CRM",
    "customers": "Clientes",
    "einvoicing": "Factura electrónica",
    "expenses": "Gastos",
    "finances": "Finanzas",
    "hr": "RRHH",
    "importer": "Importaciones",
    "inventory": "Inventario",
    "manufacturing": "Producción",
    "pos": "POS",
    "products": "Productos",
    "purchases": "Compras",
    "reconciliation": "Conciliación",
    "reports": "Reportes",
    "sales": "Ventas",
    "settings": "Configuración",
    "suppliers": "Proveedores",
    "templates": "Plantillas",
    "users": "Usuarios",
    "webhooks": "Webhooks"
  }
}
```

## Architecture Overview

### Module Naming Flow
```
Filesystem Folder Name (e.g., "compras")
        ↓
_normalize_module_name() [Backend]
        ↓
Database (e.g., "purchases")
        ↓
Frontend Module Slug Detection (toSlug())
        ↓
i18n Translation Lookup (modules.purchases)
        ↓
User sees: "Compras" (Spanish) or "Purchases" (English)
```

### Key Files Modified
1. `apps/backend/app/modules/modules_catalog/interface/http/admin.py` - Normalization function
2. `apps/backend/app/modules/modules_catalog/infrastructure/repositories.py` - Filter inactive modules
3. `apps/tenant/src/i18n/locales/es.json` - Translation mappings
4. `ops/migrations/2026-02-14_005_normalize_modules_to_english/` - Database migration
5. `ops/migrations/2026-02-14_006_delete_inactive_duplicate_modules/` - Cleanup migration

## Benefits
✓ No duplicate modules in the menu  
✓ Consistent English-only database schema  
✓ Flexible internationalization via i18n  
✓ New modules registered via "Detectar desde FS" are automatically normalized  
✓ Easy to add support for more languages in the future  

## Testing Verification
After applying these changes:
- ✓ Database has exactly 23 modules, all active with English names (lowercase)
- ✓ No duplicate or inactive modules in the database
- ✓ Each module has a corresponding Spanish translation
- ✓ "Detectar desde FS" will normalize any new folders to English
- ✓ Frontend displays Spanish text via i18n, not hardcoded in the database
- ✓ Menu shows each module only once with proper translations

## Future Considerations
- If new folder names are added with other languages (e.g., Portuguese, French), update `_normalize_module_name()` mapping
- Consider making the mapping configuration externalized (e.g., in settings) for easier maintenance
- Add validation to ensure module names are always lowercase English in the database
