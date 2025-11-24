# Próximos Pasos: Migración Completa Español→Inglés

## Estado Actual
- ✓ `company/` ya tiene archivos en inglés (es el destino final)
- ✗ `empresa/` es un duplicado en español (DELETEAR)
- ✗ `accounting/plan_cuentas.py` en español (RENOMBRAR)
- ✗ `finance/caja.py` en español (RENOMBRAR)
- ✗ `hr/nomina.py` en español (RENOMBRAR)
- ✗ `hr/empleado.py` en español (RENOMBRAR)
- ✗ `core/auditoria_importacion.py` en español (RENOMBRAR)
- ✗ Múltiples archivos con docstrings/comentarios en español

---

## EJECUCIÓN (En Orden)

### 1️⃣ PRE-CHECK: Buscar referencias a los archivos que van a cambiar
```powershell
# En PowerShell, desde la raíz del proyecto
cd "C:\Users\pc_cashabamba\Documents\GitHub\proyecto"

# Buscar imports de empresa
Select-String -Path "apps\backend\app\**\*.py" -Pattern "from app\.models\.empresa" -Recurse | Select-Object Path, LineNumber, Line

# Buscar imports de plan_cuentas, caja, nomina
Select-String -Path "apps\backend\app\**\*.py" -Pattern "plan_cuentas|from.*caja|from.*nomina" -Recurse
```

### 2️⃣ Ejecutar el script automático (paso 1-4)
```powershell
# Primero: DRY RUN (ver qué va a pasar)
.\scripts\complete_migration.ps1

# Luego: EJECUTAR (hacer los cambios)
.\scripts\complete_migration.ps1 -Execute
```

**Qué hace:**
1. Deleta `empresa/` folder
2. Renombra archivos españoles a inglés
3. Actualiza nombres de clases
4. Actualiza imports en `__init__.py`

### 3️⃣ Actualizar imports en TODO el código base
```bash
# Opción A: Usar VS Code Find & Replace (más seguro)
# Ctrl+Shift+H (o Edit > Find and Replace)
# Reemplazar:
#   from app.models.empresa import          → from app.models.company import
#   from app.models.accounting.plan_cuentas → from app.models.accounting.chart_of_accounts
#   from app.models.finance.caja            → from app.models.finance.cash_management
#   from app.models.hr.nomina               → from app.models.hr.payroll
#   from app.models.hr.empleado             → from app.models.hr.employee
#   from app.models.core.auditoria_importacion → from app.models.core.import_audit

# Opción B: Script Python
python scripts/update_imports.py --apply
```

### 4️⃣ Actualizar referencias de clases
```bash
# Usar Find & Replace para reemplazar nombres de clases:
#   PlanCuentas     → ChartOfAccounts
#   Caja            → CashManagement
#   Nomina          → Payroll
#   Empleado        → Employee
```

### 5️⃣ Actualizar docstrings y comentarios en español
**Archivos principales:**
- [ ] `core/document_line.py` - Cambiar documentación
- [ ] `core/payment.py` - Cambiar docstrings
- [ ] `core/modelsimport.py` - Cambiar comentarios
- [ ] `pos/register.py` - Cambiar docstrings
- [ ] `pos/receipt.py` - Cambiar docstrings
- [ ] `pos/doc_series.py` - Cambiar docstrings
- [ ] `production/_production_order.py` - Cambiar comentarios
- [ ] `ai/incident.py` - Cambiar nombres de campos si están en español
- [ ] `auth/useradmis.py` - Cambiar docstrings
- [ ] `models/imports.py` - Cambiar comentarios
- [ ] `models/tenant.py` - Cambiar comentarios
- [ ] `models/recipes.py` - Cambiar comentarios

### 6️⃣ Validar que no hay imports rotos
```bash
# Buscar imports que no resuelven
python -m py_compile apps/backend/app/**/*.py

# O ejecutar tests
pytest tests/ -v --tb=short
```

### 7️⃣ Ejecutar tests
```bash
cd apps/backend
pytest tests/ -v
```

---

## Archivos Clave a Revisar Después

### Routers (`app/routers/`)
Si importan modelos españoles, actualizar:
```python
# Antes
from app.models.empresa import Empresa
from app.models.finance.caja import Caja

# Después
from app.models.company import Company
from app.models.finance.cash_management import CashManagement
```

### Services (`app/services/`)
Similar a routers, buscar imports de modelos antiguos

### Schemas (Pydantic models)
Si hay schemas que heredan de los modelos, actualizar imports

### Tests (`tests/`)
Actualizar imports de fixtures y tests

---

## Diagrama de Cambios

```
ANTES:
models/
├── empresa/              ← DELETEAR
│   ├── empresa.py
│   ├── usuarioempresa.py
│   ├── rolempresas.py
│   └── usuario_rolempresa.py
├── company/
│   ├── company.py
│   ├── company_user.py
│   ├── company_role.py
│   └── company_user_role.py
├── accounting/plan_cuentas.py        ← RENOMBRAR
├── finance/caja.py                   ← RENOMBRAR
├── hr/nomina.py                      ← RENOMBRAR
├── hr/empleado.py                    ← RENOMBRAR
└── core/auditoria_importacion.py     ← RENOMBRAR

DESPUÉS:
models/
├── company/                          ✓ (ya existe, sin cambios)
│   ├── company.py
│   ├── company_user.py
│   ├── company_role.py
│   └── company_user_role.py
├── accounting/chart_of_accounts.py   ✓ RENOMBRADO
├── finance/cash_management.py        ✓ RENOMBRADO
├── hr/payroll.py                     ✓ RENOMBRADO
├── hr/employee.py                    ✓ RENOMBRADO
└── core/import_audit.py              ✓ RENOMBRADO
```

---

## Quick Checklist

- [ ] 1. Pre-check: Buscar referencias
- [ ] 2. Ejecutar `complete_migration.ps1 -Execute`
- [ ] 3. Actualizar imports en app/
- [ ] 4. Actualizar referencias de clases
- [ ] 5. Cambiar docstrings/comentarios
- [ ] 6. Validar imports
- [ ] 7. Ejecutar tests
- [ ] 8. Git commit con mensaje claro

---

## Git Commit Message
```
refactor: complete spanish to english migration

- Delete empresa/ folder (duplicate of company/)
- Rename accounting/plan_cuentas.py → accounting/chart_of_accounts.py
- Rename finance/caja.py → finance/cash_management.py
- Rename hr/nomina.py → hr/payroll.py
- Rename hr/empleado.py → hr/employee.py
- Rename core/auditoria_importacion.py → core/import_audit.py
- Update all imports across codebase
- Update class names to English
- Update docstrings and comments to English
- Remove remaining Spanish naming conventions
```

---

## Help

Si algo no funciona:
1. Revisar `git status` para ver qué cambió
2. Hacer `git diff` para ver las diferencias
3. Si algo se rompe, hacer `git checkout` para revertir
4. Ejecutar tests para encontrar el problema
