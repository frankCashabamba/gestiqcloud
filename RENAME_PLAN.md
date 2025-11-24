# Plan de Renombrado: Español → Inglés (SIN DATOS)

## Estructura Actual
```
models/
├── empresa/                    → DELETE (migrate to company/)
│   ├── empresa.py
│   ├── usuarioempresa.py
│   ├── rolempresas.py
│   ├── usuario_rolempresa.py
│   └── settings.py
├── company/                    → ALREADY EXISTS
│   ├── company.py
│   ├── company_role.py
│   ├── company_settings.py
│   ├── company_user.py
│   ├── company_user_role.py
│   └── __init__.py
├── core/
│   ├── facturacion.py          → DELETE (archivo español)
│   ├── modulo.py               → DELETE (archivo español)
│   ├── auditoria_importacion.py → RENAME
│   └── ...
├── accounting/
│   ├── plan_cuentas.py         → RENAME
│   └── __init__.py
├── finance/
│   ├── caja.py                 → RENAME
│   ├── banco.py                → RENAME (ya en inglés)
│   └── __init__.py
├── hr/
│   ├── nomina.py               → RENAME
│   ├── empleado.py             → RENAME
│   └── __init__.py
├── pos/
│   ├── register.py
│   ├── receipt.py
│   ├── doc_series.py
├── production/
│   ├── _production_order.py
├── ai/
│   ├── incident.py
└── auth/
    ├── useradmis.py
```

## Fases de Renombrado

### FASE 1: Limpiar `empresa/` → Consolidar en `company/`

**Archivos a procesar:**
- [ ] `models/empresa/empresa.py` → MERGE en `models/company/company.py`
- [ ] `models/empresa/usuarioempresa.py` → MERGE en `models/company/company_user.py`
- [ ] `models/empresa/rolempresas.py` → YA EXISTE `company/company_role.py`
- [ ] `models/empresa/usuario_rolempresa.py` → YA EXISTE `company/company_user_role.py`
- [ ] `models/empresa/settings.py` → YA EXISTE `company/company_settings.py`

**Acción**: Verificar si `company/` ya tiene todo, si sí → DELETE `empresa/`

---

### FASE 2: Renombrar archivos en `core/`

- [ ] `core/facturacion.py` → DELETE (ver si contenido va a otro lado)
- [ ] `core/modulo.py` → DELETE (ver si contenido va a otro lado)
- [ ] `core/auditoria_importacion.py` → `core/import_audit.py`
- [ ] `core/document_line.py` → Review docstrings/comentarios (español)
- [ ] `core/modelsimport.py` → REVIEW (comentarios españoles)

---

### FASE 3: Renombrar en `accounting/`

- [ ] `accounting/plan_cuentas.py` → `accounting/chart_of_accounts.py`

**Cambios dentro del archivo:**
```python
# Antes
class PlanCuentas:
    cuenta: str
    descripcion: str

# Después
class ChartOfAccounts:
    account: str
    description: str
```

---

### FASE 4: Renombrar en `finance/`

- [ ] `finance/caja.py` → `finance/cash_management.py`
- [ ] `finance/banco.py` → YA EN INGLÉS (dejar como está o renombrar a `bank.py`?)

**Cambios dentro de `caja.py` → `cash_management.py`:**
```python
# Enums
class CashMovementType(str, Enum):  # de caja_movimiento_tipo
    SALE = "sale"
    PURCHASE = "purchase"
    BANK = "bank"

class CashMovementCategory(str, Enum):  # de caja_movimiento_categoria
    INCOME = "income"
    EXPENSE = "expense"

class CashClosingStatus(str, Enum):  # de cierre_caja_status
    OPEN = "open"
    CLOSED = "closed"

# Clases
class CashMovement(Base):  # de movimiento_caja
    id: UUID
    type: CashMovementType
    amount: Decimal

class CashClosing(Base):  # de cierre_caja
    ...
```

---

### FASE 5: Renombrar en `hr/`

- [ ] `hr/nomina.py` → `hr/payroll.py`
- [ ] `hr/empleado.py` → `hr/employee.py`

**Cambios dentro:**
```python
# Enums
class PayrollStatus(str, Enum):  # de nomina_status
    ACTIVE = "active"
    INACTIVE = "inactive"

class PayrollType(str, Enum):  # de nomina_tipo
    SALARY = "salary"
    BONUS = "bonus"

# Clases
class Payroll(Base):  # de Nomina
    ...

class PayrollItem(Base):  # de NominaConcepto
    ...
```

---

### FASE 6: Revisar y limpiar docstrings/comentarios

- [ ] `core/document_line.py` - Cambiar comentarios al inglés
- [ ] `core/payment.py` - Cambiar docstrings al inglés
- [ ] `pos/register.py` - Cambiar docstrings al inglés
- [ ] `pos/receipt.py` - Cambiar docstrings al inglés
- [ ] `pos/doc_series.py` - Cambiar docstrings al inglés
- [ ] `production/_production_order.py` - Cambiar comentarios
- [ ] `ai/incident.py` - Cambiar nombres de campos españoles
- [ ] `auth/useradmis.py` - Cambiar docstrings
- [ ] `models/imports.py` - Cambiar comentarios
- [ ] `models/tenant.py` - Cambiar comentarios
- [ ] `models/recipes.py` - Cambiar comentarios

---

## Pasos Concretos por Orden

### 1. Verificar `company/` tiene todo
```bash
# Comparar empresa/ vs company/
ls -la app/models/empresa/
ls -la app/models/company/

# Si company/ tiene TODO, borrar empresa/
rm -rf app/models/empresa/
```

### 2. Renombrar archivos
```bash
cd app/models

# accounting/
mv accounting/plan_cuentas.py accounting/chart_of_accounts.py

# finance/
mv finance/caja.py finance/cash_management.py

# hr/
mv hr/nomina.py hr/payroll.py
mv hr/empleado.py hr/employee.py

# core/
mv core/auditoria_importacion.py core/import_audit.py
# DELETE core/facturacion.py y core/modulo.py (si aplica)
```

### 3. Actualizar contenido de archivos renombrados
- Cambiar nombres de clases
- Cambiar nombres de enums
- Cambiar nombres de atributos
- Actualizar imports internos

### 4. Actualizar `__init__.py` en cada directorio
```python
# Antes (accounting/__init__.py)
from .plan_cuentas import PlanCuentas

# Después
from .chart_of_accounts import ChartOfAccounts
```

### 5. Buscar y reemplazar imports en TODA la app
```bash
# En app/ (excepto models/)
grep -r "from app.models.empresa" --include="*.py" | replace
grep -r "from app.models.core.facturacion" --include="*.py" | replace
grep -r "from app.models.core.modulo" --include="*.py" | replace
grep -r "from app.models.core.plan_cuentas" --include="*.py" | replace
grep -r "from app.models.finance.caja" --include="*.py" | replace
grep -r "from app.models.hr.nomina" --include="*.py" | replace
grep -r "from app.models.accounting.plan_cuentas" --include="*.py" | replace
```

### 6. Actualizar docstrings y comentarios
Usar Find & Replace en cada archivo

---

## Checklist de Validación

- [ ] No hay carpeta `empresa/` en models
- [ ] `accounting/chart_of_accounts.py` existe y es correcto
- [ ] `finance/cash_management.py` existe y es correcto
- [ ] `hr/payroll.py` existe y es correcto
- [ ] `hr/employee.py` existe y es correcto
- [ ] `core/import_audit.py` existe y es correcto
- [ ] No hay imports rotos
- [ ] Tests pasan
- [ ] Docstrings en inglés

---

## Comandos Rápidos (Windows PowerShell)

```powershell
cd C:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app\models

# Ver estructura
tree /F

# Renombrar archivo
Rename-Item -Path "accounting\plan_cuentas.py" -NewName "chart_of_accounts.py"
Rename-Item -Path "finance\caja.py" -NewName "cash_management.py"
Rename-Item -Path "hr\nomina.py" -NewName "payroll.py"
Rename-Item -Path "hr\empleado.py" -NewName "employee.py"
Rename-Item -Path "core\auditoria_importacion.py" -NewName "import_audit.py"

# Borrar carpeta empresa (CUIDADO - verificar primero)
Remove-Item -Path "empresa" -Recurse -Force
```
