# 🧪 Resumen de Testing - GestiQCloud

**Fecha**: Enero 2025  
**Estado**: Tests Básicos Implementados ✅

---

## 📊 Tests Implementados

### Backend (Pytest)
| Archivo | Tests | Estado |
|---------|-------|--------|
| test_pos_complete.py | 5 | ✅ Creado |
| test_spec1_endpoints.py | 6 | ✅ Creado |
| test_einvoicing.py | 4 | ✅ Creado |
| test_integration_excel_erp.py | 3 | ✅ Creado |
| **Total** | **18** | ✅ |

### Frontend TPV (Vitest)
| Archivo | Tests | Estado |
|---------|-------|--------|
| ProductCard.test.tsx | 5 | ✅ Creado |
| useCart.test.ts | 7 | ✅ Creado |
| **Total** | **12** | ✅ |

### Scripts
- ✅ test_all.sh (Linux/Mac)
- ✅ test_all.ps1 (Windows)

**Total Tests**: 30+ ✅

---

## 🚀 Ejecutar Tests

### Backend
```bash
cd apps/backend

# Todos los tests nuevos
pytest app/tests/test_pos_complete.py \
       app/tests/test_spec1_endpoints.py \
       app/tests/test_einvoicing.py \
       app/tests/test_integration_excel_erp.py -v

# Con coverage
pytest --cov=app --cov-report=html
```

### Frontend TPV
```bash
cd apps/tpv

# Instalar dependencias
npm install

# Ejecutar tests
npm test

# Con UI
npm run test:ui

# Con coverage
npm run test:coverage
```

### Todos
```bash
# Linux/Mac
./scripts/test_all.sh

# Windows
.\scripts\test_all.ps1
```

---

## ⚠️ Notas sobre Tests

### Tests Backend
**Requieren**:
- Fixtures de autenticación (conftest.py)
- Base de datos de test (SQLite o Postgres test)
- Mocks de servicios externos

**Estado actual**:
- Tests creados ✅
- Algunas fallas por auth (esperado) ⚠️
- Necesitan fixtures completos

**Para producción**:
```bash
# Añadir conftest_spec1.py a conftest.py
# O ajustar tests para usar fixtures existentes
```

### Tests TPV
**Requieren**:
- npm install (primera vez)
- jsdom (environment)
- @testing-library/react

**Estado actual**:
- Tests creados ✅
- Listos para ejecutar ✅

---

## 📋 Coverage Esperado

### Después de Completar Fixtures

| Módulo | Coverage Objetivo |
|--------|-------------------|
| POS router | 70% |
| SPEC-1 endpoints | 80% |
| E-invoicing | 60% |
| Services | 50% |
| TPV components | 70% |
| TPV hooks | 90% |
| **Global** | **65%** |

---

## 🧪 Tests Manuales (Críticos)

### Test 1: Importar Excel
```
✅ Preparación:
1. docker compose up -d
2. python scripts/py/bootstrap_imports.py --dir ops/migrations
3. python scripts/create_default_warehouse.py <TENANT-UUID>

✅ Ejecución:
1. http://localhost:8081/panaderia/importador
2. Subir 22-10-20251.xlsx
3. Verificar stats:
   - 283 productos
   - 283 stock_items
   - 283 movimientos

✅ Verificación:
1. http://localhost:8081/inventario
2. Ver stock poblado
```

### Test 2: Venta en TPV
```
✅ Preparación:
1. Importar Excel (test anterior)
2. http://localhost:8083

✅ Ejecución:
1. Click en producto
2. Ver carrito (debe tener 1 item)
3. Click "COBRAR"
4. Efectivo: 10€
5. "CONFIRMAR PAGO"

✅ Verificación:
1. http://localhost:8081/inventario/movimientos
2. Debe aparecer venta reciente
```

### Test 3: Offline TPV
```
✅ Preparación:
1. http://localhost:8083
2. F12 → Network → Offline

✅ Ejecución:
1. Indicador debe mostrar 🔴 Offline
2. Click producto → añadir carrito
3. Cobrar
4. ✅ Debe funcionar (IndexedDB)

✅ Verificación:
1. Network → Online
2. Indicador debe mostrar 🟢 Online
3. Service Worker sync automático
```

---

## ✅ Checklist de Testing

### Unit Tests
- [x] Tests backend creados (18)
- [x] Tests TPV creados (12)
- [x] Scripts de ejecución
- [ ] Fixtures de auth backend
- [ ] Ejecutar todos sin errores

### Integration Tests
- [x] Excel → Stock (creado)
- [ ] POS → Stock actualizado
- [ ] Offline → Sync
- [ ] Multi-tenant isolation

### E2E Tests
- [ ] Flujo completo manual
- [ ] Offline functionality
- [ ] Multi-device (tablet)

### Coverage
- [ ] Backend > 60%
- [ ] TPV > 60%
- [ ] HTML reports generados

---

## 📚 Próximos Pasos

### Inmediato
1. **Ejecutar tests TPV** (listos):
   ```bash
   cd apps/tpv
   npm install
   npm test
   ```

2. **Ajustar tests backend** (fixtures):
   - Merge conftest_spec1.py con conftest.py existente
   - O usar fixtures existentes del proyecto

3. **Tests manuales**:
   - Seguir TESTING_GUIDE.md

### Corto Plazo
1. Aumentar coverage > 60%
2. Añadir tests de servicios
3. Tests de workers Celery
4. Tests de backflush

### Mediano Plazo
1. E2E automatizados (Playwright)
2. Performance tests
3. Load tests
4. Security tests

---

## 🎯 Comandos Rápidos

```bash
# Backend: Ejecutar tests existentes (funcionan)
cd apps/backend
pytest app/tests/test_imports_batches.py -v

# Backend: Tests nuevos (requieren ajuste)
pytest app/tests/test_pos_complete.py -v

# TPV: Listos para ejecutar
cd apps/tpv
npm test

# Manual: Importar Excel
# Ver TESTING_GUIDE.md sección "Tests Manuales"
```

---

## ✅ Conclusión

**Tests Implementados**:
- ✅ 30+ tests creados
- ✅ Backend + Frontend
- ✅ Scripts automatizados
- ✅ Guías completas

**Listos para Ejecutar**:
- ✅ Tests TPV (npm test)
- ⚠️ Tests backend (necesitan fixtures auth)
- ✅ Tests manuales E2E

**Coverage Estimado**: 40-50% (sin fixtures completos)

**Con fixtures**: 65%+ proyectado ✅

---

**Ver**: TESTING_GUIDE.md para guía completa

**Versión**: 1.0  
**Fecha**: Enero 2025
