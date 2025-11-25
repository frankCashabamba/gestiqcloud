# Análisis Detallado de Refactorización

## 1. DIRECTORIOS A RENOMBRAR

### app/modules/
```
proveedores/          → suppliers/
gastos/               → expenses/
empresa/              → company/
usuarios/             → users/
rrhh/                 → hr/ (ya existe! consolidar)
compras/              → purchases/ (OPCIONAL)
contabilidad/         → accounting/ (OPCIONAL)
ventas/               → sales/ (OPCIONAL)
facturacion/          → invoicing/ (OPTIONAL)
```

### app/models/
```
suppliers/proveedor.py           → suppliers/supplier.py (LEGACY, CHECK FIRST)
expenses/gasto.py                → expenses/expense.py
company/empresa.py               → company/company.py
company/usuario_empresa.py       → company/company_user.py
company/permiso_accion_global.py → company/global_permission.py
company/configuracion_empresa.py → company/company_config.py
```

## 2. ARCHIVOS SCHEMA A RENOMBRAR/CONSOLIDAR

```
schemas/empresa.py                     → schemas/company.py
schemas/configuracion.py               → ELIMINAR (consolidar en company.py)
schemas/configuracionempresasinicial.py → schemas/company_initial_config.py
schemas/rol_empresa.py                 → schemas/company_role.py
schemas/hr_nomina.py                   → schemas/payroll.py
```

## 3. IMPORTS CON ALIAS A ACTUALIZAR

### Archivos con alias="proveedor_id"
```
app/schemas/purchases.py:13
app/schemas/purchases.py:36
app/schemas/expenses.py:13
app/schemas/expenses.py:44
```

### Archivos importando modelos deprecated
```
app/modules/imports/domain/handlers_complete.py:423
app/modules/imports/domain/handlers.py:367
```

## 4. SETTINGS/LABELS EN ESPAÑOL

### app/services/sector_defaults.py
- "proveedores" → "suppliers"
- "gastos" → "expenses"
- "label": "Proveedor" → "label": "Supplier"
- "label": "Lote del proveedor" → "label": "Supplier Lot"
- Otros labels en español

### app/modules/rrhh/interface/http/tenant.py
- Docstring: "Gestión de nóminas" → "Payroll Management"
- "Calculadora de nóminas" → "Payroll Calculator"
- etc.

### app/schemas/hr_nomina.py
- "# CONCEPTOS DE NÓMINA" → "# PAYROLL CONCEPTS"
- "Esquemas Pydantic para sistema de nóminas" → "Pydantic schemas for payroll system"

## 5. CATALOGS EN SETTINGS

### app/modules/settings/README.md
```
| `expenses` | Gastos | finance | No | ✅ |
→ (ya está como expenses, bien!)
```

## 6. RUTAS HTTP A CONSIDERAR

```
/proveedores    → /suppliers
/gastos         → /expenses
/empresa        → /company
/rrhh           → /hr
/usuarios       → /users
```

## 7. ARCHIVOS LEGACY/COMPAT A ELIMINAR

Buscar en estos directorios:
- app/models/*/proveedor*
- app/models/*/gasto*
- app/models/*/nomina*
- app/models/*/empresa*
- app/models/*/usuario*
- app/modules/*/wrappers/
- app/modules/*/compat/

## 8. DOCSTRINGS/COMMENTS EN ESPAÑOL

Patrones a limpiar:
- """...[texto en español]..."""
- # [comentario en español]
- f"[mensaje en español]"

Excepto en:
- app/modules/imports/ (documentation files OK en español)
- Archivos .md
- comments históricos no críticos

## 9. ORDEN DE EJECUCIÓN RECOMENDADO

1. Crear mapping file con todas las búsquedas/reemplazos
2. Actualizar IMPORTS PRIMERO (antes de mover archivos)
3. Mover módulos en app/modules/
4. Mover archivos en app/models/
5. Mover/consolidar esquemas en app/schemas/
6. Limpiar docstrings y labels
7. Verificar rutas HTTP
8. Actualizar tests
9. Eliminar archivos legacy

## 10. ARCHIVOS CRÍTICOS A VERIFICAR

- app/main.py (rutas registradas)
- app/db/base.py (imports de modelos)
- app/platform/http/router.py (registros de módulos)
- app/setup.py (si existe configuración)
- alembic/env.py (migraciones)
