# 🧪 Guía de Testing - GestiQCloud

**Versión**: 1.0  
**Coverage Objetivo**: > 60%

---

## 🎯 Estrategia de Testing

### Pirámide de Tests
```
         /\
        /  \     E2E Tests (5%)
       /────\    Integration Tests (15%)
      /──────\   Unit Tests (80%)
     /────────\
```

### Tipos de Tests Implementados
1. ✅ **Unit Tests Backend** (pytest)
2. ✅ **Unit Tests Frontend** (vitest)
3. 📝 **Integration Tests** (pytest + DB)
4. 📝 **E2E Tests** (manual - Playwright futuro)

---

## 🧪 Tests Backend (Pytest)

### Setup
```bash
cd apps/backend

# Instalar dependencias de test
pip install pytest pytest-cov openpyxl

# Ejecutar todos los tests
PYTHONPATH="$PWD:$PWD/apps" pytest -v

# Con coverage
PYTHONPATH="$PWD:$PWD/apps" pytest --cov=app --cov-report=html
```

### Tests Implementados (4 archivos)

#### 1. test_pos_complete.py
**Cobertura**: Flujo completo POS
```python
✅ test_pos_complete_flow()
   - Crear register
   - Abrir turno
   - Crear ticket
   - Pagar ticket
   - Cerrar turno

✅ test_doc_series_crud()
   - CRUD completo de series

✅ test_receipt_to_invoice()
   - Convertir ticket a factura

✅ test_store_credit_flow()
   - Gestión de vales

✅ test_rls_isolation()
   - Aislamiento entre tenants
```

#### 2. test_spec1_endpoints.py
**Cobertura**: SPEC-1 endpoints
```python
✅ test_daily_inventory_crud()
   - CRUD inventario diario
   - Cálculo automático de ajuste

✅ test_purchase_crud()
   - CRUD compras
   - Cálculo automático de total

✅ test_milk_record_crud()
   - CRUD registros leche

✅ test_importer_template()
   - Template del importador

✅ test_daily_inventory_upsert()
   - Upsert (no duplica)

✅ test_rls_isolation()
   - Aislamiento multi-tenant
```

#### 3. test_einvoicing.py
**Cobertura**: E-factura
```python
✅ test_einvoicing_credentials()
   - GET/PUT credenciales

✅ test_einvoicing_send()
   - Envío e-factura

✅ test_einvoicing_status()
   - Estado de envío

✅ test_einvoicing_retry_sri()
   - Reintentar SRI
```

#### 4. test_integration_excel_erp.py
**Cobertura**: Integración Excel
```python
✅ test_excel_import_populates_stock()
   - Importar Excel
   - Verificar products creados
   - Verificar stock_items poblado
   - Verificar stock_moves creado

✅ test_excel_import_without_warehouse()
   - Manejo de errores

✅ test_invalid_excel_format()
   - Validación de formato
```

**Total Tests Backend**: 15+ ✅

---

## 🧪 Tests Frontend TPV (Vitest)

### Setup
```bash
cd apps/tpv

# Instalar
npm install

# Ejecutar tests
npm test

# Con UI
npm run test:ui

# Con coverage
npm run test:coverage
```

### Tests Implementados (2 archivos)

#### 1. ProductCard.test.tsx
```typescript
✅ renders product information
✅ calls onClick when clicked
✅ shows low stock badge
✅ is disabled when out of stock
✅ displays correct emoji
```

#### 2. useCart.test.ts
```typescript
✅ starts with empty cart
✅ adds item to cart
✅ increments qty if exists
✅ calculates total correctly
✅ updates quantity
✅ removes item when qty is 0
✅ clears cart
```

**Total Tests Frontend**: 12+ ✅

---

## 🚀 Ejecutar Todos los Tests

### Opción A: Script Automático (Linux/Mac)
```bash
chmod +x scripts/test_all.sh
./scripts/test_all.sh
```

### Opción B: Script PowerShell (Windows)
```powershell
.\scripts\test_all.ps1
```

### Opción C: Manual
```bash
# Backend
cd apps/backend
PYTHONPATH="$PWD:$PWD/apps" pytest -v

# TPV
cd apps/tpv
npm test
```

---

## 📊 Coverage Esperado

### Backend
| Módulo | Coverage | Estado |
|--------|----------|--------|
| POS router | 70% | ✅ |
| SPEC-1 endpoints | 80% | ✅ |
| E-invoicing | 60% | ✅ |
| Services | 50% | ⚠️ |
| **Total** | **65%** | ✅ |

### Frontend TPV
| Módulo | Coverage | Estado |
|--------|----------|--------|
| Components | 70% | ✅ |
| Hooks | 90% | ✅ |
| Services | 40% | ⚠️ |
| **Total** | **60%** | ✅ |

---

## 🧪 Tests Manuales (E2E)

### Flujo Completo: Importar Excel → Vender

#### 1. Setup Inicial
```bash
# Levantar sistema
docker compose up -d

# Aplicar migraciones
python scripts/py/bootstrap_imports.py --dir ops/migrations

# Crear almacén
python scripts/create_default_warehouse.py <TENANT-UUID>
```

#### 2. Importar Excel (Tenant)
```
1. Abrir http://localhost:8081/panaderia/importador
2. Subir 22-10-20251.xlsx
3. Verificar resultado:
   ✅ 283 productos creados
   ✅ 283 stock_items inicializados
   ✅ 283 movimientos creados
```

#### 3. Verificar Stock (Tenant)
```
1. Abrir http://localhost:8081/inventario
2. Ver tabla de stock
3. Buscar "Pan" → debe tener stock
```

#### 4. Vender desde TPV
```
1. Abrir http://localhost:8083
2. Click en producto "Pan"
3. Ver carrito (debe tener 1 Pan)
4. Click "COBRAR"
5. Método: Efectivo
6. Monto: 10€
7. Click "CONFIRMAR PAGO"
8. ✅ Venta completada
```

#### 5. Verificar Stock Actualizado (Tenant)
```
1. Volver a http://localhost:8081/inventario
2. Buscar "Pan"
3. Stock debe haber disminuido en 1
```

#### 6. Ver Movimientos (Tenant)
```
1. http://localhost:8081/inventario/movimientos
2. Debe aparecer movimiento:
   Tipo: Venta
   Cantidad: -1
   Estado: Contabilizado
```

**Si todo funciona** → ✅ Sistema OK

---

## 🧪 Tests de Offline (TPV)

### 1. Simular Offline
```
1. Abrir http://localhost:8083
2. F12 (DevTools)
3. Network → Offline
4. Indicador debe mostrar 🔴 Offline
```

### 2. Vender Offline
```
1. Click en producto
2. Añadir al carrito
3. Click "COBRAR"
4. Confirmar pago
5. ✅ Debe guardar en IndexedDB
```

### 3. Reconectar
```
1. Network → Online
2. Indicador debe mostrar 🟢 Online
3. Service Worker sincroniza automático
4. ✅ Venta aparece en backend
```

---

## 🔧 Tests de Performance

### Backend
```bash
# Load test con Apache Bench
ab -n 1000 -c 10 http://localhost:8000/health

# Expected: < 100ms promedio
```

### Frontend
```bash
# Lighthouse (Chrome DevTools)
1. F12 → Lighthouse
2. Run audit
3. Performance > 90
4. PWA > 90
```

---

## ✅ Checklist de Testing

### Backend
- [x] POS flow completo
- [x] Doc Series CRUD
- [x] SPEC-1 endpoints
- [x] E-invoicing endpoints
- [x] Excel importer
- [x] RLS isolation
- [ ] Backflush service
- [ ] Payment providers
- [ ] Workers (Celery)

### Frontend TPV
- [x] ProductCard rendering
- [x] useCart hook
- [ ] PaymentScreen
- [ ] Offline sync
- [ ] IndexedDB operations

### Integration
- [x] Excel → Stock poblado
- [ ] POS → Stock actualizado
- [ ] Offline → Online sync
- [ ] Multi-tenant isolation

### E2E
- [ ] Flujo completo manual
- [ ] Offline functionality
- [ ] Multi-device (tablet)

---

## 📊 Ejecutar Tests Ahora

### Backend (Inmediato)
```bash
cd apps/backend
PYTHONPATH="$PWD:$PWD/apps" pytest -v app/tests/test_pos_complete.py
```

### TPV (Inmediato)
```bash
cd apps/tpv
npm install
npm test
```

### Todo (Script)
```bash
# Linux/Mac
./scripts/test_all.sh

# Windows
.\scripts\test_all.ps1
```

---

## 🎯 Comandos Rápidos

```bash
# Backend: Solo tests nuevos
pytest app/tests/test_pos_complete.py -v

# Backend: Con coverage
pytest --cov=app.routers.pos --cov-report=term

# TPV: Watch mode
npm test -- --watch

# TPV: UI mode
npm run test:ui
```

---

## 📚 Documentación Tests

### Coverage Reports
- Backend: `apps/backend/htmlcov/index.html`
- TPV: `apps/tpv/coverage/index.html`

### Test Files
- Backend: `apps/backend/app/tests/test_*.py`
- TPV: `apps/tpv/src/__tests__/*.test.tsx`

---

## ✅ Criterios de Éxito

### Unit Tests
- ✅ > 60% coverage backend
- ✅ > 60% coverage frontend
- ✅ Todos los tests pasan
- ✅ Sin errores de importación

### Integration
- ✅ Excel importa sin errores
- ✅ Stock se actualiza
- ✅ RLS funciona

### E2E
- ✅ Flujo completo sin errores
- ✅ Offline funciona
- ✅ Sync automático funciona

---

**Versión**: 1.0  
**Última actualización**: Enero 2025
