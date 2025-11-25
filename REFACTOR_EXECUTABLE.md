# Refactorización Backend - Plan Ejecutivo Paso a Paso

## STATUS ACTUAL
✅ Algunos archivos ya renombrados (expense.py, supplier.py, company_user.py, etc.)
❌ PERO: Compat files legacy aún existen (empresa.py, usuarioempresa.py)
❌ Imports aún usan alias old-style

## PASO 1: ACTUALIZAR IMPORTS (ANTES DE ELIMINAR COMPAT FILES)

### 1.1 Reemplazar imports en toda la app

```bash
# En PowerShell, ejecutar desde raíz del proyecto:

# 1. empresa.py imports
(gci -r -i "*.py") | ForEach-Object {
    (Get-Content $_) -replace `
        'from app\.models\.company\.empresa import', `
        'from app.models.company.company import' |
    Set-Content $_
}

# 2. usuarioempresa imports
(gci -r -i "*.py") | ForEach-Object {
    (Get-Content $_) -replace `
        'from app\.models\.company\.usuarioempresa import UsuarioEmpresa', `
        'from app.models.company.company_user import CompanyUser as UsuarioEmpresa' |
    Set-Content $_
}

# 3. Mejor aún, cambiar a nombre correcto (sin alias)
(gci -r -i "*.py") | ForEach-Object {
    (Get-Content $_) -replace `
        'from app\.models\.company\.company_user import CompanyUser as UsuarioEmpresa', `
        'from app.models.company.company_user import CompanyUser' |
    Set-Content $_
}
```

### 1.2 Archivos específicos a verificar y actualizar manualmente:
- [ ] app/routers/admin/usuarios.py:12 - cambiar import
- [ ] app/core/security_cookies.py:59 - cambiar import
- [ ] app/services/sector_templates.py:13 - cambiar import

## PASO 2: RENOMBRAR DIRECTORIOS DE MÓDULOS

```bash
# PowerShell
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\modules

# Renombrar módulos
Rename-Item "proveedores" "suppliers"
Rename-Item "gastos" "expenses"
Rename-Item "empresa" "company"
Rename-Item "usuarios" "users"
Rename-Item "rrhh" "hr"  # Verificar consolidación

# Otros opcionales:
# Rename-Item "compras" "purchases"
# Rename-Item "ventas" "sales"
# Rename-Item "contabilidad" "accounting"
```

### 2.1 Actualizar imports de módulos

```python
# ANTES:
from app.modules.proveedores import ...
from app.modules.gastos import ...
from app.modules.empresa import ...

# DESPUÉS:
from app.modules.suppliers import ...
from app.modules.expenses import ...
from app.modules.company import ...
```

Buscar/reemplazar:
```
app\.modules\.proveedores → app.modules.suppliers
app\.modules\.gastos → app.modules.expenses
app\.modules\.empresa → app.modules.company
app\.modules\.usuarios → app.modules.users
```

## PASO 3: ACTUALIZAR PYDANTIC FIELDS CON ALIAS

### 3.1 Archivos a actualizar:

**app/schemas/purchases.py**
```python
# ANTES:
supplier_id: UUID | None = Field(None, alias="proveedor_id", description="Supplier ID")

# DESPUÉS:
supplier_id: UUID | None = Field(None, description="Supplier ID")
```

**app/schemas/expenses.py**
```python
# ANTES:
supplier_id: UUID | None = Field(None, alias="proveedor_id", description="Supplier ID")
expense_category_id: UUID | None = Field(None, alias="categoria_gasto_id", description="Expense category ID")

# DESPUÉS:
supplier_id: UUID | None = Field(None, description="Supplier ID")
expense_category_id: UUID | None = Field(None, description="Expense category ID")
```

## PASO 4: RENOMBRAR ESQUEMAS

```bash
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\schemas

# Renombrar archivos
Rename-Item "empresa.py" "company.py"
Rename-Item "rol_empresa.py" "company_role.py"
Rename-Item "configuracionempresasinicial.py" "company_initial_config.py"
Rename-Item "hr_nomina.py" "payroll.py"

# REVISAR:
# - configuracion.py ¿se puede eliminar o consolidar?
```

### 4.1 Actualizar imports de esquemas

```
app\.schemas\.empresa → app.schemas.company
app\.schemas\.rol_empresa → app.schemas.company_role
app\.schemas\.hr_nomina → app.schemas.payroll
```

## PASO 5: LIMPIAR SETTINGS/LABELS/DOCSTRINGS

### 5.1 app/services/sector_defaults.py
Reemplazar en configuraciones de sectores:
```python
"proveedores" → "suppliers"
"gastos" → "expenses"
"label": "Proveedor" → "label": "Supplier"
"label": "Lote del proveedor" → "label": "Supplier Batch"
"field": "proveedor" → "field": "supplier"
"field": "lote_proveedor" → "field": "supplier_batch"
```

### 5.2 Docstrings en módulos
Cambiar de Spanish → English en:
- app/modules/rrhh/interface/http/tenant.py
- app/modules/suppliers/interface/http/tenant.py
- app/modules/expenses/interface/http/tenant.py
- app/schemas/payroll.py
- Todos los nuevos esquemas

### 5.3 Catalogs/Enums
En app/modules/settings/:
- Cambiar descripción de "gastos" → "expenses"
- Cambiar descripción de "proveedores" → "suppliers"

## PASO 6: ACTUALIZAR RUTAS HTTP

En archivos que registren rutas:
- app/platform/http/router.py
- app/main.py

```python
# ANTES:
include_router_safe(r, ("app.modules.proveedores.interface.http.tenant", "router"), prefix="/tenant")

# DESPUÉS:
include_router_safe(r, ("app.modules.suppliers.interface.http.tenant", "router"), prefix="/tenant")
```

## PASO 7: ELIMINAR ARCHIVOS LEGACY/COMPAT

UNA VEZ que todos los imports estén actualizados:

```bash
# Verificar que nada importe estos:
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\models\company
Remove-Item "empresa.py"
Remove-Item "usuarioempresa.py"

# Otros si existen:
# Remove-Item "configuracion_empresa.py" (si está en models/)
```

## PASO 8: TESTS

### 8.1 Actualizar imports en tests
```
app\.models\.company\.empresa → app.models.company.company
app\.models\.company\.usuarioempresa → app.models.company.company_user
app\.schemas\.empresa → app.schemas.company
app\.schemas\.hr_nomina → app.schemas.payroll
```

### 8.2 Actualizar docstrings en tests
Cambiar comentarios de español → inglés en:
- app/tests/test_hr_nominas.py
- Otros test files

## PASO 9: VERIFICACIÓN FINAL

```bash
# Buscar cualquier referencia residual
grep -r "proveedor_id" --include="*.py" app/
grep -r "categoria_gasto_id" --include="*.py" app/
grep -r "from app.modules.proveedores" --include="*.py" app/
grep -r "from app.models.company.empresa" --include="*.py" app/
```

## CHECKLIST DE EJECUCIÓN

- [ ] Paso 1: Actualizar imports de modelos empresa/usuarioempresa
- [ ] Paso 2: Renombrar directorios módulos (proveedores→suppliers, etc)
- [ ] Paso 2.1: Actualizar imports de módulos
- [ ] Paso 3: Eliminar alias Field() en schemas
- [ ] Paso 4: Renombrar files schema
- [ ] Paso 4.1: Actualizar imports de esquemas
- [ ] Paso 5: Limpiar settings/labels/docstrings
- [ ] Paso 5.1: sector_defaults.py completado
- [ ] Paso 5.2: Docstrings convertidos a inglés
- [ ] Paso 5.3: Catalogs actualizados
- [ ] Paso 6: Rutas HTTP actualizadas
- [ ] Paso 7: Archivos legacy eliminados
- [ ] Paso 8: Tests actualizados
- [ ] Paso 9: Verificación final limpia

## ARCHIVOS CRÍTICOS POR VERIFICAR DESPUÉS

1. app/db/base.py - imports de modelos
2. app/platform/http/router.py - registros de routers
3. app/main.py - rutas iniciales
4. alembic/env.py - configuración migraciones
5. Tests - todos los imports

## NOTAS IMPORTANTES

- **NO eliminar compat files hasta estar 100% seguro de que no se usan**
- Hacer commits pequeños por cada sección
- Runear tests después de cada sección
- Verificar migraciones de BD después de cambios de modelos
- Los archivos .md en modules/imports/ pueden permanecer en español
