# Plan de Refactorización Backend - Spanish → English

## Mapeo de Renombramientos

### 1. Módulos a Renombrar
- `app/modules/proveedores/` → `app/modules/suppliers/`
- `app/modules/gastos/` → `app/modules/expenses/`
- `app/modules/rrhh/` → `app/modules/hr/` (PARCIAL - ya existe en models)
- `app/modules/empresa/` → `app/modules/company/`
- `app/modules/usuarios/` → `app/modules/users/`

### 2. Modelos a Renombrar
- `app/models/suppliers/proveedor.py` → `app/models/suppliers/supplier.py` (LEGACY)
- `app/models/expenses/gasto.py` → `app/models/expenses/expense.py`
- `app/models/company/empresa.py` → `app/models/company/company.py`
- `app/models/company/usuario_empresa.py` → `app/models/company/company_user.py`
- `app/models/company/permiso_accion_global.py` → `app/models/company/global_permission.py`
- `app/models/company/configuracion_empresa.py` → `app/models/company/company_config.py`

### 3. Esquemas a Renombrar
- `app/schemas/empresa.py` → `app/schemas/company.py`
- `app/schemas/configuracion.py` → Eliminar (consolidar en company_config)
- `app/schemas/configuracionempresasinicial.py` → `app/schemas/company_initial_config.py`
- `app/schemas/rol_empresa.py` → `app/schemas/company_role.py`
- `app/schemas/hr_nomina.py` → `app/schemas/payroll.py`

### 4. Alias/Compat Files a Eliminar
- `proveedor.py` (en cualquier lugar)
- `Proveedor*` (archivos con este nombre)
- `Gasto` (archivos)
- `Nomina*` (archivos con este nombre)
- `ConfiguracionEmpresa*`
- `Empresa*` (archivos específicos)
- `UsuarioEmpresa*`
- `PermisoAccionGlobal*`

### 5. Cambios en Imports (Alias)
```python
# ANTES:
from app.schemas import Proveedor, ProveedorCreate  # alias="proveedor_id"
from app.models.expenses.gasto import Gasto
from app.models.hr.payroll import Payroll as Nomina

# DESPUÉS:
from app.schemas.suppliers import Supplier, SupplierCreate
from app.models.expenses.expense import Expense
from app.models.hr.payroll import Payroll
```

### 6. Campos con Alias en Pydantic
```python
# ANTES:
supplier_id: UUID | None = Field(None, alias="proveedor_id")
expense_category_id: UUID | None = Field(None, alias="categoria_gasto_id")

# DESPUÉS:
supplier_id: UUID | None = Field(None)
expense_category_id: UUID | None = Field(None)
```

### 7. Labels/Mensajes en Español a Limpiar
- Docstrings en español → English
- Mensajes de error en español → English
- Labels en settings/catalogs → English
- Comentarios de código en español → English

## Fases de Ejecución

### Fase 1: Preparación
- [ ] Crear script de búsqueda-reemplazo
- [ ] Hacer backup de git
- [ ] Identificar ALL imports que usan alias

### Fase 2: Renombramiento de Módulos
- [ ] `proveedores/` → `suppliers/`
- [ ] `gastos/` → `expenses/`
- [ ] `empresa/` → `company/`
- [ ] `usuarios/` → `users/`

### Fase 3: Renombramiento de Archivos
- [ ] Modelos: `gasto.py` → `expense.py`, etc
- [ ] Esquemas: consolidar y renombrar

### Fase 4: Actualizar Imports
- [ ] Por módulo: buscar/reemplazar imports antiguos
- [ ] Eliminar alias en Field()

### Fase 5: Limpiar Contenido
- [ ] Docstrings en español
- [ ] Labels/mensajes en settings
- [ ] Catalogs/enums
- [ ] Tests

### Fase 6: Eliminar Archivos Legacy
- [ ] Archivos compat/wrapper
- [ ] Archivos duplicados
- [ ] Verificar que no haya más referencias

## Criterios de Éxito
- ✅ Cero referencias a "proveedor_id" en Pydantic (solo supplier_id)
- ✅ Cero imports de módulos spanish-name
- ✅ Cero docstrings en español en code (OK en docs)
- ✅ Tests verdes
- ✅ Migraciones de BD coherentes con nombres nuevos
