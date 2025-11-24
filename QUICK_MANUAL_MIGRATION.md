# Migración Manual Rápida: Español → Inglés

## ⏱️ Tiempo estimado: 30 minutos

---

## 🔴 PASO 1: Eliminar carpeta `empresa/` (5 min)

**En VS Code:**
1. Click derecho en `apps/backend/app/models/empresa`
2. Delete (recycle bin icon)
3. Confirmar eliminación

**Resultado esperado:** La carpeta desaparece, pero `company/` sigue intacta (es el destino correcto).

---

## 🔴 PASO 2: Renombrar archivos (10 min)

**En VS Code - Explorer:**

### 2.1 `accounting/plan_cuentas.py` → `chart_of_accounts.py`
- Click derecho en el archivo
- Rename
- Escribir: `chart_of_accounts.py`

### 2.2 `finance/caja.py` → `cash_management.py`
- Click derecho
- Rename
- Escribir: `cash_management.py`

### 2.3 `hr/nomina.py` → `payroll.py`
- Click derecho
- Rename
- Escribir: `payroll.py`

### 2.4 `hr/empleado.py` → `employee.py`
- Click derecho
- Rename
- Escribir: `employee.py`

### 2.5 `core/auditoria_importacion.py` → `import_audit.py`
- Click derecho
- Rename
- Escribir: `import_audit.py`

---

## 🟠 PASO 3: Actualizar nombres de clases en los archivos renombrados (10 min)

**Usar Find & Replace (Ctrl+H) en cada archivo:**

### 3.1 `chart_of_accounts.py`
```
Buscar:     class PlanCuentas
Reemplazar: class ChartOfAccounts

Buscar:     class Cuenta
Reemplazar: class Account
```

### 3.2 `cash_management.py`
```
Buscar:     class Caja
Reemplazar: class CashManagement

Buscar:     class CajaMovimiento
Reemplazar: class CashMovement

Buscar:     class CierreCaja
Reemplazar: class CashClosing

Buscar:     caja_movimiento_tipo
Reemplazar: cash_movement_type

Buscar:     caja_movimiento_categoria
Reemplazar: cash_movement_category

Buscar:     cierre_caja_status
Reemplazar: cash_closing_status
```

### 3.3 `payroll.py`
```
Buscar:     class Nomina
Reemplazar: class Payroll

Buscar:     class NominaConcepto
Reemplazar: class PayrollItem

Buscar:     class NominaPlantilla
Reemplazar: class PayrollTemplate

Buscar:     nomina_status
Reemplazar: payroll_status

Buscar:     nomina_tipo
Reemplazar: payroll_type
```

### 3.4 `employee.py`
```
Buscar:     class Empleado
Reemplazar: class Employee
```

### 3.5 `import_audit.py`
```
Buscar:     class AuditoriaImportacion
Reemplazar: class ImportAudit
```

---

## 🟠 PASO 4: Actualizar `__init__.py` files (5 min)

**Usar Find & Replace en cada archivo:**

### 4.1 `accounting/__init__.py`
```
Buscar:     from .plan_cuentas import
Reemplazar: from .chart_of_accounts import
```

### 4.2 `finance/__init__.py`
```
Buscar:     from .caja import
Reemplazar: from .cash_management import
```

### 4.3 `hr/__init__.py`
```
Buscar:     from .nomina import
Reemplazar: from .payroll import

Buscar:     from .empleado import
Reemplazar: from .employee import
```

### 4.4 `core/__init__.py`
```
Buscar:     from .auditoria_importacion import
Reemplazar: from .import_audit import
```

---

## 🟡 PASO 5: Actualizar imports en TODO el código (Ctrl+Shift+H para Find & Replace global)

**En VS Code - Find & Replace (global):**

```
Buscar:     from app.models.empresa import
Reemplazar: from app.models.company import

Buscar:     from app.models.accounting.plan_cuentas import
Reemplazar: from app.models.accounting.chart_of_accounts import

Buscar:     from app.models.finance.caja import
Reemplazar: from app.models.finance.cash_management import

Buscar:     from app.models.hr.nomina import
Reemplazar: from app.models.hr.payroll import

Buscar:     from app.models.hr.empleado import
Reemplazar: from app.models.hr.employee import

Buscar:     from app.models.core.auditoria_importacion import
Reemplazar: from app.models.core.import_audit import
```

**Verificar:**
- En el campo "Replace" cada una
- Mostrar un "Replace All" después de verificar que coincida lo correcto
- Click en "Replace All"

---

## 🟢 PASO 6: Verificación final (5 min)

### 6.1 Buscar imports rotos
```
Buscar: from app.models.empresa
Buscar: from app.models.core.facturacion
Buscar: from app.models.core.modulo
Buscar: from app.models.accounting.plan_cuentas (viejo)
Buscar: from app.models.finance.caja (viejo)
Buscar: from app.models.hr.nomina (viejo)
Buscar: from app.models.hr.empleado (viejo)
```

Si encuentras algo → reemplazar manualmente

### 6.2 Buscar referencias a clases antiguas
```
Buscar: PlanCuentas
Buscar: Caja
Buscar: Nomina
Buscar: Empleado
Buscar: AuditoriaImportacion
```

---

## 📝 OPCIONAL: Cambiar docstrings al inglés

Si quieres limpiar docstrings españoles (no obligatorio):

### Archivos con docstrings españoles:
- [ ] `core/document_line.py` - cambiar documentación
- [ ] `core/payment.py` - cambiar docstrings
- [ ] `pos/register.py` - cambiar docstrings
- [ ] `pos/receipt.py` - cambiar docstrings
- [ ] `pos/doc_series.py` - cambiar docstrings
- [ ] `production/_production_order.py` - cambiar comentarios
- [ ] `models/imports.py` - cambiar comentarios
- [ ] `models/tenant.py` - cambiar comentarios
- [ ] `models/recipes.py` - cambiar comentarios

**Ejemplo:**
```python
# Antes
"""Configuración de producto"""

# Después
"""Product configuration"""
```

---

## ✅ Final Checklist

- [ ] `empresa/` eliminada
- [ ] Archivos renombrados (5 archivos)
- [ ] Nombres de clases actualizados
- [ ] `__init__.py` actualizado (4 archivos)
- [ ] Imports globales actualizados
- [ ] Sin imports rotos (Ctrl+F en cada patrón)
- [ ] Tests pasan: `pytest tests/ -v`

---

## 🐛 Si algo se rompe

```bash
# Revertir cambios
git checkout -- apps/backend/app/

# O si eliminaste algo:
git restore apps/backend/app/models/empresa/
```

---

## 📊 Resultado Final Esperado

```
models/
├── company/                          ✓ INGLÉS
│   ├── company.py
│   ├── company_user.py
│   ├── company_role.py
│   └── company_user_role.py
├── accounting/chart_of_accounts.py   ✓ RENOMBRADO
├── finance/
│   ├── cash_management.py            ✓ RENOMBRADO
│   └── banco.py
├── hr/
│   ├── payroll.py                    ✓ RENOMBRADO
│   ├── employee.py                   ✓ RENOMBRADO
└── core/
    ├── import_audit.py               ✓ RENOMBRADO
    └── ...
```

**Todas las carpetas `empresa/`, `facturacion/`, `plan_cuentas/`, etc. → ELIMINADAS o CONSOLIDADAS**

---

## ⏳ Estimado Total: 30-45 minutos

1. Eliminar: 5 min
2. Renombrar: 10 min
3. Actualizar clases: 10 min
4. Actualizar `__init__`: 5 min
5. Actualizar imports globales: 10 min
6. Verificación: 5 min

**Total: ~45 minutos de trabajo manual**
