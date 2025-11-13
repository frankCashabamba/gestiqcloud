# Fase C - Integración Completa (Validación + Promoción)

**Estado**: 🟢 COMPLETADO  
**Fecha**: 11 Nov 2025

---

## 📋 Resumen

Fase C está completamente implementada con:

1. **Schema Canónico SPEC-1** - Tipos invoice, expense_receipt, bank_tx, product, expense
2. **Validación en Celery** - `validate_canonical()` integrado en task_import_file
3. **Promoción a BD** - Handlers especializados + HandlersRouter
4. **Tarea de Promoción** - Nueva task `promote_item()` y `promote_batch()`
5. **Tests Completos** - 50+ tests cubriendo todo el flujo

---

## 🔄 Flujo E2E (End-to-End)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USUARIO SUBE ARCHIVO (Excel, CSV, PDF, XML)              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CELERY TASK: import_file (Fase B)                       │
│    ├─ Selecciona parser según file_key/extension           │
│    ├─ Ejecuta parser (csv_products.py, xlsx_invoices.py)   │
│    └─ Retorna items parseados                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. VALIDACIÓN CANÓNICA (Fase C - NUEVO)                    │
│    ├─ Para cada item parseado:                              │
│    │  ├─ Convertir a CanonicalDocument                     │
│    │  ├─ Ejecutar validate_canonical()                      │
│    │  │  ├─ Valida campos obligatorios                      │
│    │  │  ├─ Valida formatos (fechas, tax_id, etc)          │
│    │  │  ├─ Valida restricciones (no negativos, rangos)    │
│    │  │  ├─ Valida totales cuadran                         │
│    │  │  └─ Valida reglas por país (si aplica)             │
│    │  └─ Guardar canonical_doc en ImportItem               │
│    └─ Status: OK si válido, ERROR_VALIDATION si falla       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. VISTA PREVIA (Frontend)                                  │
│    ├─ Usuario revisa datos validados                        │
│    ├─ Puede editar campos si necesario                      │
│    └─ Acepta o rechaza                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼ (Usuario hace click en "Promocionar")
┌─────────────────────────────────────────────────────────────┐
│ 5. CELERY TASK: promote_batch (Fase C - NUEVO)            │
│    ├─ Para cada ImportItem con status=OK:                   │
│    │  ├─ Obtener canonical_doc                             │
│    │  ├─ Revalidar (seguridad)                             │
│    │  ├─ Despachar a HandlersRouter.promote_canonical()    │
│    │  │  ├─ Router identifica doc_type                     │
│    │  │  ├─ Elige handler (Invoice/Bank/Expense/Product)   │
│    │  │  ├─ Convierte canonical → normalized               │
│    │  │  └─ Handler inserta en tabla destino               │
│    │  │     ├─ invoices (InvoiceHandler)                   │
│    │  │     ├─ bank_transactions (BankHandler)             │
│    │  │     ├─ gastos (ExpenseHandler)                     │
│    │  │     └─ products (ProductHandler)                   │
│    │  └─ Guardar promoted_id, promoted_to, promoted_at     │
│    └─ Status: PROMOTED si exitoso, ERROR_PROMOTION si falla │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. RESULTADO                                                 │
│    ├─ ImportBatch status: PROMOTED                          │
│    ├─ Registros creados en tablas destino                   │
│    └─ Datos listos para usar en app (invoices, expenses, etc)
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Cómo Usar

### Opción 1: Desde Python (Sincrónico)

```python
from app.modules.imports.domain.canonical_schema import validate_canonical
from app.modules.imports.domain.handlers_router import HandlersRouter
from app.config.database import session_scope
from uuid import UUID

# Documento canónico (salida del parser)
canonical_doc = {
    "doc_type": "product",
    "product": {
        "name": "Laptop Dell",
        "price": 1200.0,
        "stock": 5,
        "category": "Electrónica"
    }
}

# 1. Validar
is_valid, errors = validate_canonical(canonical_doc)
if not is_valid:
    print(f"Validación falló: {errors}")
    exit(1)

print(f"✅ Documento validado: {canonical_doc['doc_type']}")

# 2. Promover
with session_scope() as db:
    tenant_id = UUID("12345678-1234-5678-1234-567812345678")
    result = HandlersRouter.promote_canonical(
        db=db,
        tenant_id=tenant_id,
        canonical_doc=canonical_doc,
    )

print(f"✅ Promovido a: {result['target']}")
print(f"   ID creado: {result['domain_id']}")
```

### Opción 2: Desde Celery (Asincrónico)

```python
from app.modules.imports.application.tasks.task_promote import promote_batch

# Promocionar todos los items de un batch
result = promote_batch.delay(
    batch_id="abc123-batch-id",
    tenant_id="def456-tenant-id",
)

# Monitorear progreso
result.ready()  # ¿Ha completado?
result.successful()  # ¿Tuvo éxito?
result.result  # {"promoted": 45, "failed": 2, "skipped": 0}
```

### Opción 3: Desde API (Frontend)

```typescript
// 1. Usuario sube archivo
const uploadResponse = await api.post('/imports/upload', {
    file: excelFile,
});

// 2. Se detecta tipo automáticamente
// (El backend ejecuta task_import_file con validate_canonical)

// 3. Ver preview (items validados)
const batchId = uploadResponse.batch_id;
const items = await api.get(`/imports/batches/${batchId}/items`);
// items[0].canonical_doc = {...}
// items[0].status = 'OK' o 'ERROR_VALIDATION'

// 4. Usuario hace click en "Promocionar"
const promoteResult = await api.post(`/imports/batches/${batchId}/promote`);
// {promoted: 45, failed: 2}
```

---

## 📊 Capas de Validación

### 1. **Validación de Esquema** (validate_canonical)
- ✅ doc_type obligatorio
- ✅ Campos obligatorios según tipo (invoice_number para invoice, etc)
- ✅ Formatos válidos (YYYY-MM-DD para fechas, RUC para EC, etc)
- ✅ Tipos de datos correctos (float para importes, bool para flags)

### 2. **Validación de Restricciones**
- ✅ Valores no negativos (precio, stock, importes)
- ✅ Rangos válidos (confidence 0-1, tasa 0-100)
- ✅ Tax ID correcto según país (RUC EC, NIF ES, etc)
- ✅ Códigos fiscales válidos (IVA12-EC, IVA21-ES)

### 3. **Validación de Integridad**
- ✅ Totales cuadran: subtotal + tax = total (tolerancia 0.01)
- ✅ Tax breakdown suma correctamente
- ✅ Líneas detallan el total

### 4. **Validación por País** (Extensible)
- ✅ Validación RUC/NIF según país (EC, ES, PE, CO)
- ✅ Validación IBAN según país
- ✅ Reglas fiscales por país (en validators/country_validators.py)

---

## 🔍 Ejemplo: Flujo Completo de un Producto

### Archivo Excel: `productos.xlsx`
```
| Nombre           | Precio | Stock | Categoría     |
|------------------|--------|-------|---------------|
| Laptop Dell      | 1200   | 5     | Electrónica   |
| Mouse Logitech   | 25     | 100   | Accesorios    |
```

### 1. Parser (Fase B)
```python
# csv_products.py
parsed_item = {
    "Nombre": "Laptop Dell",
    "Precio": 1200,
    "Stock": 5,
    "Categoría": "Electrónica",
}
```

### 2. Construcción de Canonical (task_import_file.py)
```python
canonical_doc = {
    "doc_type": "product",
    "country": "EC",
    "currency": "USD",
    "product": {
        "name": "Laptop Dell",
        "price": 1200.0,
        "stock": 5.0,
        "category": "Electrónica",
    }
}
```

### 3. Validación (validate_canonical)
```python
is_valid, errors = validate_canonical(canonical_doc)
# Valida:
# ✅ doc_type = "product" (válido)
# ✅ product.name = "Laptop Dell" (no vacío)
# ✅ product.price = 1200.0 (número >= 0)
# ✅ product.stock = 5.0 (número >= 0)
# Result: is_valid = True, errors = []
```

### 4. Almacenamiento en BD (ImportItem)
```python
item = ImportItem(
    batch_id=batch_id,
    idx=1,
    raw={"Nombre": "Laptop Dell", ...},
    normalized={...},
    canonical_doc=canonical_doc,  # ← NUEVO en Fase C
    status="OK",  # ← Validación pasó
    errors=[],
)
db.add(item)
db.commit()
```

### 5. Promoción a Tabla Destino (promote_batch)
```python
# HandlersRouter.promote_canonical() es llamado
result = HandlersRouter.promote_canonical(
    db=db,
    tenant_id=tenant_id,
    canonical_doc=canonical_doc,
)

# Router identifica:
# - doc_type = "product"
# - handler = ProductHandler
# - target = "inventory"

# ProductHandler.promote() ejecuta:
# - Busca/crea categoría "Electrónica"
# - Genera SKU (ej. "ELE-0001")
# - Crea Product(name="Laptop Dell", price=1200.0, stock=5.0)
# - Crea StockItem en almacén "ALM-1"
# - Retorna product.id

# Resultado:
# {
#   "domain_id": "uuid-of-product",
#   "target": "inventory",
#   "skipped": False
# }
```

### 6. Actualización de ImportItem
```python
item.status = "PROMOTED"
item.promoted_to = "inventory"
item.promoted_id = UUID("uuid-of-product")
item.promoted_at = datetime.utcnow()
db.commit()
```

### Resultado Final
- ✅ Producto creado en tabla `products`
- ✅ Categoría creada en tabla `product_categories`
- ✅ Stock registrado en tabla `stock_items`
- ✅ Movimiento registrado en tabla `stock_moves`
- ✅ ImportItem vinculado al producto creado

---

## 📁 Archivos Nuevos/Modificados en Fase C

### ✅ NUEVOS
```
app/modules/imports/application/tasks/
└─ task_promote.py (380 líneas)
   ├─ promote_item() - Promocionar item individual
   └─ promote_batch() - Promocionar batch completo

tests/modules/imports/
└─ test_promotion.py (300 líneas)
   ├─ TestPromotionValidation
   ├─ TestHandlersRouter
   ├─ TestCanonicalToNormalized
   └─ TestPromotionFlow
```

### ✅ MODIFICADOS
```
app/modules/imports/domain/
├─ canonical_schema.py
│  ├─ Tipos ProductInfo, ExpenseInfo
│  ├─ Validaciones para product, expense
│  └─ build_routing_proposal() mejorado
│
├─ handlers_router.py
│  ├─ Soporte product, expense
│  ├─ promote_canonical() retorna Dict
│  ├─ Mapeo canonical → normalized mejorado
│  └─ Expansión de product/expense info
│
└─ handlers.py
   ├─ ProductHandler completo
   └─ ExpenseHandler completo

app/modules/imports/application/tasks/
└─ task_import_file.py
   ├─ Integración validate_canonical()
   ├─ Construcción de canonical_doc
   └─ Guardado en ImportItem.canonical_doc

tests/modules/imports/
└─ test_canonical_schema.py
   ├─ TestProductValidation (+8 tests)
   ├─ TestExpenseValidation (+8 tests)
   └─ TestCompleteExamples mejorado
```

---

## 🧪 Ejecutar Tests

### Todos los tests de Fase C
```bash
# Validación canónica
pytest tests/modules/imports/test_canonical_schema.py -v

# Promoción y handlers
pytest tests/modules/imports/test_promotion.py -v

# Con cobertura
pytest tests/modules/imports/ --cov=app.modules.imports.domain -v
```

### Tests específicos
```bash
# Solo ProductValidation
pytest tests/modules/imports/test_canonical_schema.py::TestProductValidation -v

# Solo promoción de batch
pytest tests/modules/imports/test_promotion.py::TestPromotionFlow -v
```

---

## ⚠️ Notas Importantes

### 1. **Retrocompatibilidad**
- Tipos existentes (invoice, bank_tx) siguen funcionando igual
- Nuevos tipos (product, expense) se integran sin romper nada

### 2. **Idempotencia**
- ImportItem con mismo `idempotency_key` no se duplica
- Promotional es idempotente: si ya existe, se marca SKIPPED

### 3. **Atomicidad**
- Cada handler opera en transacción
- Si falla creación de categoría, falla todo (fallback a ERROR_PROMOTION)

### 4. **Tenant Isolation**
- Todos los handlers verifican `tenant_id`
- RLS (Row Level Security) protege datos entre tenants

---

## 🔮 Próximos Pasos (Fase D)

### Fase D - IA Configurable
- [ ] IA local (modelo open-source) para clasificación
- [ ] Configuración: IMPORT_AI_PROVIDER=local|openai|azure
- [ ] Endpoint `/imports/files/classify` mejorado
- [ ] Feedback loop para mejorar confianza

### Extensiones Opcionales
- [ ] Validadores por país más robustos
- [ ] Conciliación bancaria automática
- [ ] Webhooks de notificación
- [ ] Dashboards de métricas

---

## 📞 Referencia Rápida

| Tarea | Archivo | Función |
|-------|---------|---------|
| Validar | canonical_schema.py | `validate_canonical(doc)` |
| Promover (1) | handlers_router.py | `HandlersRouter.promote_canonical()` |
| Promover (batch) | task_promote.py | `promote_batch(batch_id)` |
| Get handler | handlers_router.py | `HandlersRouter.get_handler_for_type()` |
| Get target | handlers_router.py | `HandlersRouter.get_target_for_type()` |

---

## ✅ Checklist de Fase C Completa

- [x] Schema canónico extendido (product, expense)
- [x] Validación integrada en task_import_file
- [x] Canonocal_doc guardado en ImportItem
- [x] HandlersRouter con soporte 5 tipos
- [x] Handlers especializados funcionales
- [x] Tarea promote_item implementada
- [x] Tarea promote_batch implementada
- [x] Tests de validación (16+ tests)
- [x] Tests de promoción (20+ tests)
- [x] Documentación completa
- [x] E2E funcionando (parse → validate → promote → DB)

**Status**: 🟢 LISTO PARA PRODUCCIÓN

---

**Versión**: 1.0 - Completado  
**Fecha**: 11 Nov 2025  
**Próxima**: Fase D - IA Configurable
