# Refactorización Backend - Guía Rápida

## 0. PREPARACIÓN (5 min)

```bash
cd c:\Users\pc_cashabamba\Documents\GitHub\proyecto

# Commit actual para poder revertir
git add .
git commit -m "Pre-refactor checkpoint"
git branch refactor/spanish-to-english
```

## 1. ANÁLISIS (5 min)

```bash
# Ver qué necesita cambiar
python refactor_script.py --analyze

# Esto mostrará:
# - Archivos con imports old-style
# - Archivos con aliases de Pydantic
# - Archivos con labels en español
```

## 2. AUTOMÁTICO (2 min)

```bash
# Ejecutar cambios automáticos
python refactor_script.py --execute

# Responder "y" cuando pregunte
```

## 3. VERIFICACIÓN (2 min)

```bash
# Confirmar que todo se aplicó
python refactor_script.py --verify
```

## 4. CAMBIOS MANUALES NECESARIOS

### 4.1 Renombrar directorios de módulos

```powershell
cd apps\backend\app\modules

# Renombrar carpetas
Rename-Item "proveedores" "suppliers"
Rename-Item "gastos" "expenses"
Rename-Item "empresa" "company"
Rename-Item "usuarios" "users"

# Verificar si rrhh existe y consolidar
ls -Name | ? {$_ -like "*rrhh*" -or $_ -like "*hr*"}
```

### 4.2 Renombrar esquemas

```powershell
cd ..\schemas

# Renombrar archivos schema
Rename-Item "empresa.py" "company.py"
Rename-Item "rol_empresa.py" "company_role.py"
Rename-Item "configuracionempresasinicial.py" "company_initial_config.py"
Rename-Item "hr_nomina.py" "payroll.py"

# Ver si configuracion.py se puede eliminar
# (consolidar en company_settings.py o company_initial_config.py)
ls -Name config*
```

### 4.3 Renombrar archivos modelo (si existen legacy)

```powershell
cd ..\models\company

# Eliminar compat files (DESPUÉS de verificar imports)
Remove-Item "empresa.py"
Remove-Item "usuarioempresa.py"

# Listar lo que queda
ls *.py | Select-Object Name
```

### 4.4 Revisar archivos críticos manualmente

**app/platform/http/router.py**
```python
# Buscar y cambiar estos strings:
# "app.modules.proveedores" → "app.modules.suppliers"
# "app.modules.gastos" → "app.modules.expenses"
# "app.modules.empresa" → "app.modules.company"
```

**app/main.py**
```python
# Si hay referencias a rutas/módulos antiguos, actualizar
# Especialmente si hay includes_router("proveedores", ...)
```

**app/db/base.py**
```python
# Verificar imports de modelos
# Buscar líneas como:
# from app.models.company.empresa import ...
# from app.modules.proveedores.infrastructure.models import ...
```

### 4.5 Limpiar docstrings - MANUAL (15 min)

Buscar en estos archivos y cambiar docstrings de español → inglés:

```bash
# Archivos a limpiar (docsstrings/comentarios en español):
- app/modules/suppliers/interface/http/tenant.py (si existe)
- app/modules/expenses/interface/http/tenant.py (si existe)
- app/modules/company/interface/http/tenant.py (si existe)
- app/schemas/payroll.py
- app/schemas/company.py
- app/models/expenses/expense.py (docstring)
- app/models/suppliers/supplier.py (docstring)
```

Ejemplo:
```python
# ANTES:
"""Modelo de Proveedor - Sistema de proveedores"""

# DESPUÉS:
"""Supplier Model - Supplier management system"""
```

## 5. ACTUALIZAR TESTS (10 min)

```bash
# Buscar imports old-style en tests
grep -r "from app.models.company.empresa" apps/backend/tests/
grep -r "from app.schemas.empresa" apps/backend/tests/

# Actualizar manualmente o usar script:
python refactor_script.py --execute  # (repetir para tests)
```

**app/tests/test_hr_nominas.py**
```python
# Cambiar docstrings/comentarios de español → inglés
# "Tests de Módulo de Nóminas" → "Payroll Module Tests"
# "Nómina" → "Payroll"
```

## 6. VERIFICACIÓN FINAL (10 min)

```bash
# Buscar referencias residuales
grep -r "proveedor_id" --include="*.py" apps/backend/app/
grep -r "categoria_gasto_id" --include="*.py" apps/backend/app/
grep -r "from app.modules.proveedores" --include="*.py" apps/backend/app/
grep -r "from app.modules.gastos" --include="*.py" apps/backend/app/
grep -r "from app.models.company.empresa" --include="*.py" apps/backend/app/
grep -r "from app.models.company.usuarioempresa" --include="*.py" apps/backend/app/

# Si no hay resultados = ✅ LIMPIO

# Ejecutar tests
cd apps/backend
pytest tests/ -v

# Si todo verde = ✅ LISTO
```

## 7. LIMPIAR Y COMMIT

```bash
# Eliminar archivos de refactorización
Remove-Item refactor_script.py
Remove-Item REFACTOR_*.md

# Commit final
git add -A
git commit -m "refactor: Spanish to English - models/schemas/modules/imports"
git push origin refactor/spanish-to-english

# Crear PR para review
```

## CHECKLISTA DE EJECUCIÓN

- [ ] 0. Preparación - git commit/branch
- [ ] 1. Análisis - python refactor_script.py --analyze
- [ ] 2. Automático - python refactor_script.py --execute
- [ ] 3. Verificación - python refactor_script.py --verify
- [ ] 4.1 Renombrar módulos (PowerShell)
- [ ] 4.2 Renombrar esquemas (PowerShell)
- [ ] 4.3 Renombrar modelos (PowerShell)
- [ ] 4.4 Revisar archivos críticos
- [ ] 4.5 Limpiar docstrings (MANUAL - 15 min)
- [ ] 5. Actualizar tests
- [ ] 6. Verificación final (grep + pytest)
- [ ] 7. Limpiar y commit

## TIEMPO TOTAL ESTIMADO: 60-75 minutos

- Automático: 12 min
- Manuales: 35-45 min
- Verificación: 10-15 min

## SI ALGO SALE MAL

```bash
# Revertir a checkpoint anterior
git reset --hard HEAD~1
git checkout main

# O si ya hiciste push:
git revert <commit-hash>
```

## ARCHIVOS GENERADOS PARA REFERENCIA

- `REFACTOR_PLAN.md` - Plan detallado
- `REFACTOR_ANALYSIS.md` - Análisis completo de cambios
- `REFACTOR_EXECUTABLE.md` - Instrucciones paso a paso
- `refactor_script.py` - Script de automación
- `REFACTOR_QUICK_START.md` - Este archivo
