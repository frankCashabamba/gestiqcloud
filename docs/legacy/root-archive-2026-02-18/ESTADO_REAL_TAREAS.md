# ✅/❌ ESTADO REAL DE TAREAS

**Verificación hecha:** 2026-02-16 por revisión de código

---

## TAREAS BLOQUEANTES (SEGÚN MASTER PLAN vs REALIDAD)

### 1. ✅ LIFO COSTING - IMPLEMENTADO PERO SIN TESTS

**Status:** CÓDIGO EXISTE ❌ TESTS NO

**Código actual:**
- Archivo: `apps/backend/app/services/inventory_costing.py`
- Métodos: `apply_inbound_lifo()` (línea 164) y `apply_outbound_lifo()` (línea 194)
- Están COMPLETOS y FUNCIONALES

**QUÉ FALTA:**
- ❌ Test: `test_inventory_costing_lifo()` 
- No existe en `test_inventory_costing.py`
- Solo hay test para WAC (weighted average cost)

**TAREA:** Agregar 1 test case para LIFO

---

### 2. ✅ DISCOUNT_PCT - IMPLEMENTADO

**Status:** ✅ LISTO

**Código actual:**
- Archivo: `apps/backend/app/modules/sales/interface/http/tenant.py`
- Línea 57: `discount_pct: float = Field(default=0, ge=0, le=100)`
- Campo `discount_pct` en `OrderItemIn`
- ✅ Se usa en creación de órdenes

**QUÉ FALTA:**
- ✅ NADA - Ya implementado

**TAREA:** Nada, ya está

---

### 3. ✅ INVOICE-FROM-ORDER - IMPLEMENTADO

**Status:** ✅ LISTO

**Código actual:**
- Archivo: `apps/backend/app/modules/sales/interface/http/conversions.py`
- Endpoint: `POST /sales_orders/{order_id}/invoice` (línea 58)
- Función: `create_invoice_from_sales_order()` (línea 59)
- ✅ Validaciones completas
- ✅ Conversión DocumentConverter
- ✅ GET endpoint para obtener invoice (línea 139)

**QUÉ FALTA:**
- ✅ NADA - Ya implementado y funcionando

**TAREA:** Nada, ya está

---

### 4. ⚠️ MYPY BLOQUEANTE - NO ESTÁ HABILITADO

**Status:** ❌ CONFIG NO BLOQUEANTE

**Config actual:**
- Archivo: `apps/backend/pyproject.toml`
- Línea 55-75: Tool.mypy
- **NO HAY `exit_code = 1`**
- Solo warnings, no bloquea builds
- Gradual typing solo para algunos módulos

**QUÉ FALTA:**
- ❌ Cambiar config para que sea bloqueante
- ❌ Opción: `exit_code = 1` o similar

**TAREA:** 1 línea de config

---

### 5. ❌ STOCK TRANSFERS - NO EXISTE

**Status:** ❌ 0% IMPLEMENTADO

**Búsqueda hecha:**
- No hay archivo con "stock_transfer" en nombre
- No hay modelo en `models/`
- No hay endpoint en routers
- No hay test

**QUÉ FALTA:**
- ❌ Modelo: `StockTransfer` (tabla DB)
- ❌ CRUD service
- ❌ 4 endpoints (GET, POST, PATCH, DELETE)
- ❌ Tests
- ❌ Migration SQL

**TAREA:** Implementar completo (2-3 horas)

---

## RESUMEN REAL

| # | Tarea | Estado | Falta | Tiempo |
|---|-------|--------|-------|--------|
| 1 | LIFO Costing | Código ✅ | Test ❌ | 30 min |
| 2 | Discount % | ✅ LISTO | Nada | 0 min |
| 3 | Invoice-from-Order | ✅ LISTO | Nada | 0 min |
| 4 | Mypy Bloqueante | Config ❌ | 1 línea | 5 min |
| 5 | Stock Transfers | ❌ NADA | TODO | 2-3h |

**TOTAL QUE FALTA:** 3-4 horas (NO 6-7h como dije)

---

## 🎯 LO QUE REALMENTE NECESITAS HACER AHORA

### Tarea 1: Agregar test LIFO (30 min)
```python
# En: apps/backend/app/tests/test_inventory_costing.py
# Agregar función:

def test_inventory_costing_lifo(db: Session, tenant_minimal):
    """Test LIFO costing - last in first out"""
    # Setup layers con fechas diferentes
    # Consume qty
    # Validar que consume desde más reciente
    pass
```

### Tarea 2: Mypy bloqueante (5 min)
```toml
# En: apps/backend/pyproject.toml
# Cambiar line 55-75 para agregar:

[tool.mypy]
exit_code = 1
# ... resto igual
```

### Tarea 3: Stock Transfers (2-3 horas)
- Crear modelo DB
- CRUD service
- 4 endpoints
- Tests

---

## CONCLUSIÓN

**De las 5 "tareas bloqueantes":**
- 2 YA ESTÁN HECHAS (Invoice, Discount)
- 1 ESTÁ CASI HECHA (LIFO falta solo test)
- 1 NECESITA 1 LÍNEA (Mypy config)
- 1 NO EXISTE (Stock Transfers - opcional anyway)

**LO QUE REALMENTE BLOQUEA PARA 100%:**
1. Test para LIFO (obligatorio, test suite)
2. Config Mypy (obligatorio, CI/CD)
3. Stock Transfers (bonito pero no crítico)

**TIEMPO REAL PARA 100%:** 1-2 HORAS (no 6-7h)

---

## ¿EMPEZAMOS A HACER CÓDIGO?

Dime si quieres que implemente:
1. Test LIFO
2. Mypy bloqueante
3. Stock Transfers

O cualquier otra cosa que realmente falta.
