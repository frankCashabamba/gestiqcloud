# Model Naming Normalization - Implementation Status

## Completed Steps

### 1. Folder & File Renames
- [x] Created `/app/models/company/` folder (replacement for `empresa`)
- [x] Created `/app/models/company/company.py` with all core company models
- [x] Created `/app/models/company/company_role.py` (CompanyRole model)
- [x] Created `/app/models/company/company_user.py` (CompanyUser model)
- [x] Created `/app/models/company/company_user_role.py` (CompanyUserRole model)
- [x] Created `/app/models/company/company_settings.py` (CompanySettings, InventorySettings)
- [x] Renamed `/app/models/sales/venta.py` → `/app/models/sales/sale.py`
- [x] Created `/app/models/suppliers/supplier.py` (copy of proveedor.py)
- [x] Confirmed `/app/models/purchases/purchase.py` exists (renamed from compra.py)

### 2. Model Updates
- [x] Updated `/app/models/sales/sale.py` field names:
  - `cliente_id` → `customer_id`
  - `fecha` → `date`
  - `estado` → `status`
  - `notas` → `notes`
  - `usuario_id` → `user_id`
  - `cliente` relationship → `customer`

### 3. Import Updates
- [x] Updated `/app/models/sales/__init__.py` to import from `.sale` (not `.venta`)
- [x] Updated `/app/models/purchases/__init__.py` to import from `.purchase` (not `.compra`)
- [x] Updated `/app/models/suppliers/__init__.py` to import from `.supplier` (not `.proveedor`)
- [x] Updated `/app/models/__init__.py` main imports to use company folder

## Remaining Steps

### 1. Remove Old Files/Folders (After Testing)
- [ ] Remove `/app/models/empresa/` folder (keep for now for compatibility)
- [ ] Remove `/app/models/sales/venta.py` (after testing)
- [ ] Remove `/app/models/purchases/compra.py` (after testing)
- [ ] Remove `/app/models/suppliers/proveedor.py` (after testing)

### 2. Update All Import Statements in Codebase
- [ ] Search & replace all `from app.models.empresa` → `from app.models.company`
- [ ] Search & replace all `from app.models.sales.venta` → `from app.models.sales.sale`
- [ ] Search & replace all `from app.models.purchases.compra` → `from app.models.purchases.purchase`
- [ ] Search & replace all `from app.models.suppliers.proveedor` → `from app.models.suppliers.supplier`

### 3. Normalize Finance/Cash Models
- [ ] Update `/app/models/finance/caja.py`:
  - `caja_movimiento_tipo` enum → `cash_movement_type`
  - `caja_movimiento_categoria` enum → `cash_movement_category`
  - `cierre_caja_status` enum → `cash_closing_status`
  - Update all field names to English (already done for most)

### 4. Update Remaining Model Fields
- [ ] Purchase model fields (if not already in English)
- [ ] Supplier model fields (if not already in English)
- [ ] All enum names and constraints to English

### 5. Documentation & Docstrings
- [ ] Convert docstrings from Spanish to English in:
  - `/app/models/core/document_line.py`
  - `/app/models/core/modelsimport.py`
  - `/app/models/production/_production_order.py`
  - `/app/models/recipes.py`
  - `/app/models/inventory/alerts.py`
  - All company models

### 6. Migration Generation
- [ ] Run: `python ops/scripts/generate_schema_sql.py --skip-drop false`
- [ ] Verify:
  - All table names match new models
  - All column names are correct (customer_id, date, status, etc.)
  - All constraints use English names
  - All enums are renamed properly

### 7. Testing
- [ ] Test migration on empty database: `python ops/scripts/migrate_all_migrations.py`
- [ ] Run application: `python -m pytest tests/ -q`
- [ ] Verify backward compatibility aliases work

### 8. Cleanup
- [ ] Remove all legacy aliases after confirming no references
- [ ] Remove old modelo files
- [ ] Remove old folder structures
- [ ] Final import validation

## Files Still Needing Attention

### High Priority
```
app/models/company/*.py - Complete implementations
app/models/finance/caja.py - Enum naming
app/models/purchases/purchase.py - Field validation
app/models/suppliers/supplier.py - Field validation
```

### Medium Priority
```
app/models/core/*.py - Docstrings
app/models/production/*.py - Docstrings
app/models/recipes.py - Docstrings
app/models/inventory/alerts.py - Docstrings
```

### Low Priority
```
Various routers, modules, services - Update imports as needed
Tests - Update test imports
Configuration files - Update references as needed
```

## Backward Compatibility Strategy

All new models include legacy aliases:
- `Venta` = `Sale`
- `Compra` = `Purchase`
- `Proveedor` = `Supplier`
- `UsuarioEmpresa` = `CompanyUser`
- `RolEmpresa` = `CompanyRole`
- `SectorPlantilla` = `SectorTemplate`

This allows gradual migration of the codebase without breaking existing imports.

## Migration Database Impact

New tables/schemas:
- `company_roles` (new)
- `company_users` (new)
- `company_user_roles` (new)
- `company_settings` (new)

Renamed columns:
- `sales.cliente_id` → `sales.customer_id`
- `sales.fecha` → `sales.date`
- `sales.estado` → `sales.status`
- `sales.notas` → `sales.notes`
- `sales.usuario_id` → `sales.user_id`

New enums (finance):
- `cash_movement_type`
- `cash_movement_category`
- `cash_closing_status`
