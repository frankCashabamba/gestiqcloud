# UUID Standardization Migration Summary

## Overview
Standardized all Pydantic schemas to use **UUID** consistently instead of `int | str` or mixed types.

## Files Updated

### Core Schemas
- ✅ **app/schemas/base.py** (NEW)
  - Created reusable base classes: `UUIDBase`, `TenantMixin`, `BaseEntity`

- ✅ **app/schemas/configuracion.py**
  - `AuthenticatedUser`: `user_id: int | str` → `user_id: UUID`
  - `AuthenticatedUser`: `tenant_id: int | str | None` → `tenant_id: UUID | None`

### Usuarios Module
- ✅ **app/modules/usuarios/infrastructure/schemas.py**
  - `UsuarioEmpresaOut`: `id: int | str` → `id: UUID`
  - `UsuarioEmpresaOut`: `tenant_id: int | str` → `tenant_id: UUID`

### Empresa Module
- ✅ **app/modules/empresa/interface/http/schemas.py**
  - `EmpresaOutSchema`: `id: int | UUID` → `id: UUID`

### Módulos Module
- ✅ **app/modules/schemas.py**
  - `ModuloOut`: `id: int` → `id: UUID`
  - `EmpresaModuloOut`: `id: int` → `id: UUID` (tenant_id already UUID)
  - `ModuloAsignadoOut`: `id: int` → `id: UUID` (tenant_id already UUID)
  - `EmpresaModuloOutAdmin`: `id: int` → `id: UUID` (tenant_id already UUID)

### Facturación Module
- ✅ **app/modules/facturacion/schemas.py**
  - `ClienteSchema`: `id: str` → `id: UUID`
  - `InvoiceOut`: `id: str` → `id: UUID`
  - `FacturaOut`: `id: str` → `id: UUID`

### Ventas Module
- ✅ **app/modules/ventas/interface/http/schemas.py**
  - `VentaOut`: `id: str` → `id: UUID`

### Clientes Module
- ✅ **app/modules/clients/interface/http/schemas.py**
  - `ClienteOutSchema`: `id: str` → `id: UUID`

### CRM Module
- ✅ **app/modules/crm/application/schemas.py**
  - Already using UUID consistently ✓

### Imports Module
- ✅ **app/modules/imports/schemas.py**
  - Already using UUID consistently ✓

## Pattern Applied

### Before
```python
class UsuarioEmpresaOut(UsuarioEmpresaBase):
    id: int | str
    tenant_id: int | str
```

### After
```python
from uuid import UUID

class UsuarioEmpresaOut(UsuarioEmpresaBase):
    id: UUID
    tenant_id: UUID
```

## Benefits
1. **Type Safety**: Eliminates ambiguous `int | str` unions
2. **Consistency**: Single source of truth for ID types
3. **Clarity**: Developers immediately understand expected format
4. **Conversion**: Pydantic automatically converts strings to UUIDs when possible

## Notes
- No database changes needed (UUIDs are already in DB)
- Pydantic will auto-validate UUID format on input
- Invalid UUIDs will raise clear validation errors
- Can reuse `BaseEntity` from `app/schemas/base.py` for future schemas
