# 📊 Análisis de Tests Existentes

**Fecha:** 03 Noviembre 2025
**Total tests:** 32 archivos
**Estado:** Revisión para nueva estructura

---

## ✅ TESTS VÁLIDOS (Mantener)

### Infraestructura y Core (11 tests)
```
✅ test_utils.py                    - Utilidades generales
✅ test_session_middleware.py       - Middleware de sesiones
✅ test_cookies_attrs.py            - Atributos de cookies
✅ test_login.py                    - Autenticación
✅ test_me.py                       - Usuario actual
✅ test_admin_set_password.py       - Admin funciones
✅ test_admin_empresas.py           - Admin empresas
✅ test_admin_config_modern.py      - Configuración admin
✅ test_shared_patterns.py          - Patrones compartidos
✅ test_crud_base_compat.py         - Compatibilidad CRUD
✅ test_debug_routes.py             - Rutas debug
```

### Módulos Core (8 tests)
```
✅ test_empresa_module.py           - Módulo empresas
✅ test_usuarios_module.py          - Módulo usuarios
✅ test_modulos_module.py           - Sistema de módulos
✅ test_modulos_endpoints.py        - Endpoints módulos
✅ test_electric_conflicts.py       - Conflictos ElectricSQL
✅ test_einvoicing.py               - E-facturación (actualizar)
✅ test_products_router.py          - Router productos
✅ test_repo_ventas_compat.py       - Compatibilidad ventas
```

### Importador (8 tests) - ⭐ Críticos
```
✅ test_imports_pipeline.py         - Pipeline completo
✅ test_imports_batches.py          - Batches
✅ test_imports_validators.py       - Validadores
✅ test_imports_dedupe.py           - Deduplicación
✅ test_imports_limits.py           - Límites
✅ test_imports_bulk_ops.py         - Operaciones masivas
✅ test_imports_extras.py           - Extras
✅ test_imports_photos.py           - Fotos/OCR
```

### Smoke Tests (3 tests)
```
✅ test_smoke.py                    - Smoke test general
✅ test_smoke_pg.py                 - Smoke test Postgres
✅ test_smoke_pos_pg.py             - Smoke test POS
```

### Config (1 test)
```
✅ conftest.py                      - Configuración pytest
```

**Total válidos:** 31/32 tests ✅

---

## ⚠️ TESTS A ACTUALIZAR

### test_einvoicing.py
**Razón:** Ahora tenemos `einvoicing_complete.py` con más endpoints

**Acción:** Extender tests para cubrir:
- POST /certificates
- GET /certificates/status
- DELETE /certificates/{country}
- GET /stats
- GET /list

### test_smoke_pos_pg.py
**Razón:** Ahora POS tiene más funcionalidades (refunds, store_credits)

**Acción:** Añadir tests para:
- Devoluciones
- Vales (store credits)
- Impresión

---

## 🆕 TESTS A CREAR (Módulos Nuevos)

### 1. test_production.py (~200 líneas)
```python
# Tests de producción:
- Crear orden de producción
- Calcular ingredientes necesarios
- Iniciar producción
- Completar producción
- Verificar consumo de stock automático
- Verificar generación de producto terminado
- Cancelar orden
- Estadísticas
```

### 2. test_hr_nominas.py (~180 líneas)
```python
# Tests de nóminas:
- Crear empleado
- Calcular nómina automática
- Crear nómina manual
- Aprobar nómina
- Pagar nómina
- Verificar conceptos
- Plantillas de nómina
- Estadísticas
```

### 3. test_finance_caja.py (~150 líneas)
```python
# Tests de caja:
- Crear movimiento entrada
- Crear movimiento salida
- Calcular saldo
- Crear cierre diario
- Verificar cuadre
- Estadísticas
```

### 4. test_accounting.py (~200 líneas)
```python
# Tests de contabilidad:
- Crear plan de cuentas
- Crear asiento contable
- Verificar debe = haber
- Contabilizar asiento
- Consultar balance
- Pérdidas y ganancias
- Libro mayor
```

### 5. test_sector_config.py (~150 líneas)
```python
# Tests de configuración multi-sector:
- Obtener defaults Panadería
- Obtener defaults Retail
- Obtener defaults Restaurante
- Obtener defaults Taller
- Verificar campos específicos por sector
- Verificar categorías por sector
```

**Total nuevos:** 5 archivos (~880 líneas)

---

## 🗑️ TESTS A ELIMINAR

### test.zip
**Razón:** Archivo zip (no es un test)
**Acción:** ❌ Eliminar

---

## 📋 PLAN DE ACCIÓN

### PASO 1: Ejecutar Tests Existentes
```bash
cd apps/backend
PYTHONPATH="$PWD:$PWD/apps" pytest -q app/tests -v
```

**Objetivo:** Verificar que los 31 tests pasan

### PASO 2: Eliminar test.zip
```bash
rm apps/backend/app/tests/test.zip
```

### PASO 3: Crear Nuevos Tests (5 archivos)
- test_production.py
- test_hr_nominas.py
- test_finance_caja.py
- test_accounting.py
- test_sector_config.py

### PASO 4: Actualizar Tests Existentes (2 archivos)
- test_einvoicing.py → Añadir tests de certificados
- test_smoke_pos_pg.py → Añadir tests de refunds

### PASO 5: Ejecutar Suite Completa
```bash
pytest -v
pytest --cov=app --cov-report=html
```

---

## 🎯 PRIORIDAD DE TESTING

### CRÍTICO (Ahora)
1. ✅ test_sector_config.py - Validar configuración multi-sector
2. ✅ test_production.py - Validar órdenes de producción + stock
3. ✅ Ejecutar smoke tests existentes

### ALTA (Hoy)
4. test_hr_nominas.py - Validar cálculos salariales
5. test_accounting.py - Validar asientos cuadrados

### MEDIA (Mañana)
6. test_finance_caja.py - Validar cierres de caja
7. Actualizar test_einvoicing.py

### BAJA (Futuro)
8. Tests e2e con Playwright
9. Tests de carga/performance

---

## 📊 MÉTRICAS DE TESTING

### Estado Actual
```
Tests existentes:     31 ✅
Tests obsoletos:      1 ❌
Tests a crear:        5 🆕
Tests a actualizar:   2 ⚠️

Total final esperado: 37 tests
Cobertura objetivo:   >80%
```

---

**Próxima acción:** Ejecutar tests existentes para establecer baseline
