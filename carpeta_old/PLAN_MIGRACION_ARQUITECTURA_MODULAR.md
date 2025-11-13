# PLAN DE MIGRACIÓN A ARQUITECTURA MODULAR DDD

**Fecha:** 2025-11-06  
**Estado:** ✅ La mayoría de módulos YA ESTÁN MIGRADOS  
**Acción requerida:** Limpiar duplicaciones en `main.py`

---

## 🎯 RESUMEN EJECUTIVO

### Hallazgos de la Auditoría

**BUENAS NOTICIAS:** La arquitectura modular DDD **ya está implementada** en la mayoría de módulos.

**PROBLEMA REAL:** `main.py` monta routers duplicados desde `/routers/` cuando ya existen en `/modules/`.

**SOLUCIÓN:** Limpiar `main.py` eliminando imports de routers legacy ya migrados.

---

## 📊 ESTADO REAL DEL PROYECTO

### Módulos COMPLETAMENTE Migrados ✅

| Módulo | Router en /modules/ | Router Legacy en /routers/ | Estado | Acción |
|--------|---------------------|----------------------------|--------|--------|
| **POS** | ✅ `modules/pos/interface/http/tenant.py` | ❌ Eliminado | ✅ Completo | Mantener |
| **Productos** | ✅ `modules/productos/interface/http/tenant.py` | ❌ Eliminado | ✅ Completo | Mantener |
| **E-invoicing** | ✅ `modules/einvoicing/interface/http/tenant.py` | ⚠️ `routers/einvoicing_complete.py` | 🔄 Parcial | Fusionar complete |
| **RRHH** | ✅ `modules/rrhh/interface/http/tenant.py` | ⚠️ `routers/hr.py`, `hr_complete.py` | 🔄 Verificar | Comparar contenido |
| **Finanzas** | ✅ `modules/finanzas/interface/http/tenant.py` | ⚠️ `routers/finance.py`, `finance_complete.py` | 🔄 Verificar | Comparar contenido |
| **Contabilidad** | ✅ `modules/contabilidad/interface/http/tenant.py` | ⚠️ `routers/accounting.py` | 🔄 Verificar | Comparar contenido |

### Módulos con Estructura Parcial 🔄

| Módulo | Tiene /interface/http/ | Estado |
|--------|----------------------|--------|
| **Producción** | ⚠️ Solo estructura vacía | Migrar desde `routers/production.py` |
| **Compras** | ❓ Verificar | Migrar desde `routers/purchases.py` |
| **Gastos** | ❓ Verificar | Migrar desde `routers/expenses.py` |
| **Ventas** | ❓ Verificar | Verificar vs `routers/sales.py` |
| **Proveedores** | ❓ Verificar | Verificar vs `routers/suppliers.py` |

### Routers Legacy a Eliminar ❌

Estos routers en `/routers/` están duplicados o deprecados:

```python
# main.py - ELIMINAR estos imports:

# ❌ DUPLICADO - Ya existe en modules/rrhh/
from app.routers.hr import router as hr_router  # Línea 298
from app.routers.hr_complete import router as hr_complete_router  # Línea 307

# ❌ DUPLICADO - Ya existe en modules/finanzas/
from app.routers.finance import router as finance_router  # Línea 289
from app.routers.finance_complete import router as finance_complete_router  # Línea 325

# ❌ DUPLICADO - Ya existe en modules/contabilidad/
from app.routers.accounting import router as accounting_router  # Línea 334

# ⚠️ FUSIONAR - Agregar a modules/einvoicing/
from app.routers.einvoicing_complete import router as einvoicing_complete_router  # Línea 343

# ⚠️ MIGRAR - Crear en modules/produccion/
from app.routers.production import router as production_router  # Línea 316
from app.routers.recipes import router as recipes_router  # (si existe)

# ⚠️ VERIFICAR - ¿Están en modules/?
from app.routers.purchases import router as purchases_router  # Línea 271
from app.routers.expenses import router as expenses_router  # Línea 280
from app.routers.sales import router as sales_router  # Línea 253
from app.routers.suppliers import router as suppliers_router  # Línea 262
```

### Routers a MANTENER en /routers/ ✅

Estos son servicios transversales sin módulo dedicado:

```python
# ✅ MANTENER - Servicios transversales
from app.routers.payments import router as payments_router
from app.routers.notifications import router  # (si existe)
from app.routers.categorias import router  # Compartido
from app.routers.sector_plantillas import router
from app.routers.tenant_config import router
from app.routers.settings_router import router
from app.routers.admin_stats import router
from app.routers.admin_scripts import router  # (si existe)
from app.routers.dashboard_kpis import router
```

---

## 🚀 PLAN DE ACCIÓN

### FASE 1: Verificación y Comparación (1-2 días)

**Objetivo:** Confirmar qué está implementado en cada módulo

#### Tarea 1.1: Comparar RRHH

```bash
# Verificar endpoints en módulo
grep "@router" apps/backend/app/modules/rrhh/interface/http/tenant.py

# Verificar endpoints en routers legacy
grep "@router" apps/backend/app/routers/hr.py
grep "@router" apps/backend/app/routers/hr_complete.py

# ¿Son los mismos? → Eliminar legacy
# ¿Falta algo en módulo? → Migrar primero
```

- [ ] Comparar endpoints de `modules/rrhh/` vs `routers/hr*.py`
- [ ] Documentar diferencias
- [ ] Si módulo está completo → Eliminar legacy de `main.py`
- [ ] Si módulo incompleto → Migrar faltantes

#### Tarea 1.2: Comparar Finanzas

```bash
grep "@router" apps/backend/app/modules/finanzas/interface/http/tenant.py
grep "@router" apps/backend/app/routers/finance.py
grep "@router" apps/backend/app/routers/finance_complete.py
```

- [ ] Comparar endpoints de `modules/finanzas/` vs `routers/finance*.py`
- [ ] Documentar diferencias
- [ ] Si módulo está completo → Eliminar legacy de `main.py`
- [ ] Si módulo incompleto → Migrar faltantes

#### Tarea 1.3: Comparar Contabilidad

```bash
grep "@router" apps/backend/app/modules/contabilidad/interface/http/tenant.py
grep "@router" apps/backend/app/routers/accounting.py
```

- [ ] Comparar endpoints
- [ ] Documentar diferencias
- [ ] Si módulo está completo → Eliminar legacy de `main.py`
- [ ] Si módulo incompleto → Migrar faltantes

#### Tarea 1.4: Verificar Compras, Gastos, Ventas, Proveedores

```bash
# Verificar si existen módulos con HTTP
ls -la apps/backend/app/modules/compras/interface/http/
ls -la apps/backend/app/modules/gastos/interface/http/
ls -la apps/backend/app/modules/ventas/interface/http/
ls -la apps/backend/app/modules/proveedores/interface/http/
```

- [ ] Verificar existencia de módulos
- [ ] Si existen → Comparar con routers legacy
- [ ] Si no existen → Crear estructura y migrar

---

### FASE 2: Limpieza de main.py (1 día)

**Objetivo:** Eliminar imports duplicados confirmados

#### Tarea 2.1: Comentar Imports Duplicados

Editar `apps/backend/app/main.py`:

```python
# ❌ ELIMINADO - Ya existe en modules/rrhh/interface/http/tenant.py
# from app.routers.hr import router as hr_router
# app.include_router(hr_router, prefix="/api/v1")

# ❌ ELIMINADO - Ya existe en modules/rrhh/interface/http/tenant.py  
# from app.routers.hr_complete import router as hr_complete_router
# app.include_router(hr_complete_router, prefix="")

# ❌ ELIMINADO - Ya existe en modules/finanzas/interface/http/tenant.py
# from app.routers.finance import router as finance_router
# app.include_router(finance_router, prefix="/api/v1")

# ❌ ELIMINADO - Ya existe en modules/finanzas/interface/http/tenant.py
# from app.routers.finance_complete import router as finance_complete_router
# app.include_router(finance_complete_router, prefix="")

# ❌ ELIMINADO - Ya existe en modules/contabilidad/interface/http/tenant.py
# from app.routers.accounting import router as accounting_router
# app.include_router(accounting_router, prefix="")
```

#### Tarea 2.2: Verificar platform/http/router.py

Confirmar que `platform/http/router.py` monta correctamente los módulos:

```bash
grep "include_router" apps/backend/app/platform/http/router.py
```

- [ ] Verificar que monta `modules/rrhh/`
- [ ] Verificar que monta `modules/finanzas/`
- [ ] Verificar que monta `modules/contabilidad/`
- [ ] Verificar que monta `modules/pos/`
- [ ] Verificar que monta `modules/productos/`
- [ ] Verificar que monta `modules/einvoicing/`

#### Tarea 2.3: Testing Post-Limpieza

```bash
# Iniciar backend
docker compose up -d backend

# Verificar logs
docker logs -f backend

# Probar endpoints (debe seguir funcionando)
curl http://localhost:8082/api/v1/rrhh/empleados
curl http://localhost:8082/api/v1/finanzas/caja
curl http://localhost:8082/api/v1/accounting/accounts
```

- [ ] Backend inicia sin errores
- [ ] Swagger UI carga correctamente
- [ ] Endpoints de RRHH responden
- [ ] Endpoints de Finanzas responden
- [ ] Endpoints de Contabilidad responden
- [ ] No hay errores 404

---

### FASE 3: Migraciones Pendientes (2-3 días)

#### 3.1: Migrar Producción ⚠️ ALTA PRIORIDAD

**Estado:** Estructura vacía en `modules/produccion/`, código en `routers/production.py`

```bash
# 1. Revisar código legacy
cat apps/backend/app/routers/production.py

# 2. Copiar a módulo
cp apps/backend/app/routers/production.py \
   apps/backend/app/modules/produccion/interface/http/tenant.py

# 3. Ajustar imports y añadir RBAC/RLS
# Editar modules/produccion/interface/http/tenant.py
```

**Checklist:**
- [ ] Copiar código de `routers/production.py`
- [ ] Ajustar imports
- [ ] Agregar dependencias RBAC/RLS:
  ```python
  router = APIRouter(
      prefix="/production/orders",
      dependencies=[
          Depends(with_access_claims),
          Depends(require_scope("tenant")),
          Depends(ensure_rls),
      ]
  )
  ```
- [ ] Probar endpoints en Swagger
- [ ] Eliminar import de `main.py`
- [ ] Eliminar `routers/production.py`

#### 3.2: Fusionar E-invoicing Complete

**Estado:** Base en módulo, funcionalidades extra en `routers/einvoicing_complete.py`

```bash
# 1. Ver qué endpoints tiene complete
grep "@router" apps/backend/app/routers/einvoicing_complete.py

# 2. Agregar faltantes a módulo
# Editar modules/einvoicing/interface/http/tenant.py
```

**Checklist:**
- [ ] Identificar endpoints únicos en `einvoicing_complete.py`
- [ ] Agregar a `modules/einvoicing/interface/http/tenant.py`
- [ ] Consolidar schemas
- [ ] Probar endpoints
- [ ] Eliminar `routers/einvoicing_complete.py`

#### 3.3: Migrar Recetas (si existe)

```bash
# Verificar si existe
ls apps/backend/app/routers/recipes.py

# Migrar a módulo producción
# (las recetas son parte del módulo de producción)
```

- [ ] Verificar existencia de `routers/recipes.py`
- [ ] Migrar a `modules/produccion/interface/http/recipes.py`
- [ ] Agregar RBAC/RLS
- [ ] Probar endpoints

---

### FASE 4: Verificar y Migrar Módulos Menores (2-3 días)

Para cada uno: **Compras, Gastos, Ventas, Proveedores**

**Template de verificación:**

```bash
# 1. ¿Existe módulo?
ls -la apps/backend/app/modules/{compras|gastos|ventas|proveedores}/interface/http/

# 2. Si NO existe → Crear estructura
mkdir -p apps/backend/app/modules/compras/{domain,application,infrastructure,interface/http}

# 3. Copiar código legacy
cp apps/backend/app/routers/purchases.py \
   apps/backend/app/modules/compras/interface/http/tenant.py

# 4. Ajustar imports + RBAC/RLS

# 5. Probar y eliminar legacy
```

**Checklist por módulo:**
- [ ] Compras: Verificar/Migrar/Limpiar
- [ ] Gastos: Verificar/Migrar/Limpiar
- [ ] Ventas: Verificar/Migrar/Limpiar
- [ ] Proveedores: Verificar/Migrar/Limpiar

---

### FASE 5: Eliminar Archivos Legacy (1 día)

**Solo después de confirmar que todo funciona:**

```bash
# Backup primero
mkdir -p backups/routers_legacy
cp apps/backend/app/routers/*.py backups/routers_legacy/

# Eliminar archivos migrados
rm apps/backend/app/routers/hr.py
rm apps/backend/app/routers/hr_complete.py
rm apps/backend/app/routers/finance.py
rm apps/backend/app/routers/finance_complete.py
rm apps/backend/app/routers/accounting.py
rm apps/backend/app/routers/production.py
rm apps/backend/app/routers/einvoicing_complete.py
# ... etc
```

**Checklist:**
- [ ] Backup de `/routers/` completo
- [ ] Confirmar que módulos funcionan (1 semana en producción)
- [ ] Eliminar archivos legacy
- [ ] Commit con mensaje claro: "chore: remove legacy routers (migrated to /modules/)"

---

## 📋 CHECKLIST DE VALIDACIÓN

### Pre-Limpieza
- [x] Auditoría de módulos completada
- [ ] Comparación módulo vs legacy documentada
- [ ] Plan de acción definido

### Durante Migración
- [ ] Cada módulo probado individualmente
- [ ] RBAC/RLS aplicado en todos los endpoints
- [ ] No hay errores 404
- [ ] Swagger UI muestra endpoints correctos

### Post-Limpieza
- [ ] Backend inicia sin errores
- [ ] Todos los endpoints funcionan
- [ ] Frontend puede consumir APIs
- [ ] No hay duplicaciones
- [ ] Archivos legacy eliminados
- [ ] Documentación actualizada

---

## 🔧 COMANDOS ÚTILES

### Verificar Duplicaciones

```bash
# Ver qué routers monta main.py
grep "from app.routers" apps/backend/app/main.py | grep -v "^#"

# Ver qué módulos tienen HTTP
find apps/backend/app/modules -name "tenant.py" -path "*/interface/http/*"

# Comparar endpoints
grep "@router" apps/backend/app/routers/hr.py
grep "@router" apps/backend/app/modules/rrhh/interface/http/tenant.py
```

### Testing Rápido

```bash
# Iniciar backend
docker compose up -d backend

# Ver logs en tiempo real
docker logs -f backend | grep "router mounted"

# Probar endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8082/api/v1/rrhh/empleados
```

### Rollback de Emergencia

```bash
# Si algo falla, restaurar main.py
git checkout apps/backend/app/main.py

# Reiniciar backend
docker compose restart backend
```

---

## 📊 PROGRESO

### Módulos Migrados

```
Total: 16 módulos core
Completos:   3  (19%)  ████░░░░░░░░░░░░
Verificar:   3  (19%)  ████░░░░░░░░░░░░
Pendientes: 10  (62%)  ████████████░░░░

Archivos en /routers/: 34
A eliminar tras migración: ~15-20
Mantener (transversales): ~10-15
```

---

## 🎯 SIGUIENTE PASO INMEDIATO

**ACCIÓN:** Comparar contenido de `modules/rrhh/` vs `routers/hr*.py`

```bash
# 1. Ver endpoints en módulo
grep -A 2 "@router" apps/backend/app/modules/rrhh/interface/http/tenant.py

# 2. Ver endpoints en legacy
grep -A 2 "@router" apps/backend/app/routers/hr.py
grep -A 2 "@router" apps/backend/app/routers/hr_complete.py

# 3. Comparar y decidir:
#    - ¿Son idénticos? → Eliminar legacy
#    - ¿Falta algo? → Migrar primero
```

---

**Estado:** 🟢 Plan actualizado con hallazgos reales  
**Última actualización:** 2025-11-06  
**Próxima acción:** Comparar RRHH, Finanzas y Contabilidad
