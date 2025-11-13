# 🚀 Plan de Desarrollo - Módulos Pendientes al 100%

**Fecha inicio:** 03 Noviembre 2025  
**Objetivo:** Completar todos los módulos pendientes al 100% profesional, modular y multi-sector  
**Metodología:** Sin pruebas, solo código productivo (testing posterior)

---

## 📋 Checklist General

### ✅ FASE 1: Configuración Multi-Sector (Quick Wins)
- [ ] field_config.py → SECTOR_DEFAULTS completos
- [ ] SectorPlantilla → Config JSON por sector
- [ ] Categorías por defecto por sector

### ✅ FASE 2: Facturación E-Invoicing
- [ ] Endpoints REST /api/v1/einvoicing/*
- [ ] Integración workers Celery (ya existentes)
- [ ] Schemas request/response

### ✅ FASE 3: Producción
- [ ] Modelo ProductionOrder
- [ ] Endpoints órdenes de producción
- [ ] Consumo automático de stock
- [ ] Frontend OrderForm.tsx

### ✅ FASE 4: RRHH
- [ ] Modelo Nomina completo
- [ ] Endpoints cálculo nóminas
- [ ] Frontend NominaForm.tsx
- [ ] Refactor naming (Empleado → List.tsx)

### ✅ FASE 5: Finanzas (Caja)
- [ ] Modelo CajaMovimiento
- [ ] Modelo CierreCaja
- [ ] Endpoints completos /api/v1/finanzas/caja/*
- [ ] Frontend CajaForm.tsx, List.tsx

### ✅ FASE 6: Contabilidad
- [ ] Modelo PlanCuentas
- [ ] Modelo AsientoContable
- [ ] Endpoints /api/v1/contabilidad/*
- [ ] Frontend AsientoForm.tsx

---

## 🎯 Criterios de Completitud

Cada módulo debe cumplir:

### Backend (100%)
```python
✅ Modelos SQLAlchemy completos con tenant_id
✅ Router FastAPI con CRUD completo
✅ Schemas Pydantic (Create, Update, Response, List)
✅ RLS aplicado (ensure_rls/get_current_user)
✅ Validaciones de negocio
✅ Relaciones entre modelos
✅ Índices de performance
```

### Frontend (100%)
```typescript
✅ Form.tsx con configuración dinámica
✅ List.tsx con paginación/filtros/ordenamiento
✅ services.ts con tipos TypeScript completos
✅ Routes.tsx configurado
✅ manifest.ts con metadata correcta
✅ Integración con field_config API
```

### Multi-Sector (100%)
```python
✅ SECTOR_DEFAULTS en field_config.py
✅ Campos específicos por sector
✅ Labels personalizables
✅ Categorías por defecto
✅ Config JSON en SectorPlantilla
```

---

## 📂 Estructura de Archivos a Crear

```
apps/backend/app/
├── models/
│   ├── production/
│   │   └── production_order.py          # NUEVO
│   ├── hr/
│   │   └── nomina.py                    # COMPLETAR
│   └── finance/
│       ├── caja_movimiento.py           # NUEVO
│       └── cierre_caja.py               # NUEVO
│   └── accounting/
│       ├── plan_cuentas.py              # NUEVO
│       └── asiento_contable.py          # NUEVO
│
├── routers/
│   ├── einvoicing.py                    # COMPLETAR endpoints REST
│   ├── production.py                    # NUEVO
│   └── accounting.py                    # NUEVO
│
├── schemas/
│   ├── production.py                    # NUEVO
│   ├── hr_nomina.py                     # NUEVO
│   ├── finance_caja.py                  # NUEVO
│   └── accounting.py                    # NUEVO
│
└── services/
    ├── field_config.py                  # COMPLETAR SECTOR_DEFAULTS
    └── production_service.py            # NUEVO

apps/tenant/src/modules/
├── produccion/
│   ├── OrderForm.tsx                    # NUEVO
│   └── OrdersList.tsx                   # NUEVO
│
├── rrhh/
│   ├── List.tsx                         # RENOMBRAR desde EmpleadosList.tsx
│   ├── Form.tsx                         # RENOMBRAR desde EmpleadoForm.tsx
│   └── NominaForm.tsx                   # NUEVO
│
└── finanzas/
    ├── CajaForm.tsx                     # NUEVO
    └── CajaList.tsx                     # NUEVO (renombrar existente)

ops/migrations/
├── 2025-11-03_200_production_orders/    # NUEVO
├── 2025-11-03_201_hr_nominas/           # NUEVO
├── 2025-11-03_202_finance_caja/         # NUEVO
└── 2025-11-03_203_accounting/           # NUEVO
```

---

## 🔄 Orden de Desarrollo

### DÍA 1-2: FASE 1 - Configuración
```
1. field_config.py → SECTOR_DEFAULTS completos (8 sectores x 9 módulos)
2. Crear SectorPlantilla seeds para RETAIL/BAZAR y RESTAURANTE
3. Testing manual con curl
```

### DÍA 3-4: FASE 2 - Facturación
```
1. Endpoints REST /api/v1/einvoicing/send
2. Endpoints REST /api/v1/einvoicing/status/{id}
3. Schemas request/response
4. Integración con workers Celery existentes
```

### DÍA 5-7: FASE 3 - Producción
```
1. Modelo ProductionOrder + migration
2. Router production.py completo
3. Consumo automático de stock
4. Frontend OrderForm.tsx
```

### DÍA 8-10: FASE 4 - RRHH
```
1. Modelo Nomina completo + migration
2. Endpoints cálculo nóminas
3. Frontend NominaForm.tsx
4. Refactor naming
```

### DÍA 11-13: FASE 5 - Finanzas
```
1. Modelos CajaMovimiento + CierreCaja + migration
2. Endpoints /api/v1/finanzas/caja/* completos
3. Frontend CajaForm.tsx, CajaList.tsx
```

### DÍA 14-16: FASE 6 - Contabilidad
```
1. Modelos PlanCuentas + AsientoContable + migration
2. Endpoints /api/v1/contabilidad/* básicos
3. Frontend AsientoForm.tsx
```

---

## 📏 Estándares de Código

### Python (Backend)
```python
# Naming conventions
- Clases: PascalCase
- Funciones: snake_case
- Constantes: UPPER_SNAKE_CASE
- Variables privadas: _prefijo

# Imports order
1. Standard library
2. Third-party
3. Local app

# Type hints obligatorios
def create_order(order_data: OrderCreate, db: Session) -> Order:
    ...

# Docstrings
"""
Brief description.

Args:
    param1: Description
    param2: Description

Returns:
    Description

Raises:
    HTTPException: When...
"""
```

### TypeScript (Frontend)
```typescript
// Naming conventions
- Componentes: PascalCase
- Funciones: camelCase
- Tipos: PascalCase con sufijo
- Constantes: UPPER_SNAKE_CASE

// Tipos explícitos
type Order = {
  id: string
  numero: string
  fecha: string
  estado: string
}

// Async/await en lugar de .then()
const data = await fetchOrders()

// Destructuring de props
function OrderForm({ order, onSave }: OrderFormProps) { ... }
```

---

## 🔧 Comandos de Verificación

```bash
# Backend
cd apps/backend
python -m pytest apps/backend/app/tests -v  # (posterior)
ruff check app/
mypy app/

# Frontend  
cd apps/tenant
npm run build
npm run type-check

# Migraciones
python scripts/py/bootstrap_imports.py --dir ops/migrations

# Health check
curl http://localhost:8000/api/v1/health
```

---

## 📊 Métricas de Éxito

Al finalizar todas las fases:

```
✅ 14 módulos al 100% (5 existentes + 9 nuevos)
✅ ~15,000 líneas de código profesional
✅ 100% multi-sector compatible
✅ 0 warnings de type-check
✅ 0 errores de linter
✅ Migraciones auto-aplicables
✅ Documentación README por módulo
```

---

## 🚀 Estado Actual

**Fecha:** 03 Noviembre 2025  
**Fase:** 1 - Configuración Multi-Sector  
**Progreso:** 0%

---

**Última actualización:** 03 Noviembre 2025  
**Autor:** Equipo GestiQCloud
