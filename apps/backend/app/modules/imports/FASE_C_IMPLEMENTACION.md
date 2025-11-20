# Fase C - Validación y Handlers
## Guía de Implementación

**Estado**: En progreso (60% completado)
**Última actualización**: 2025-11-11

---

## 📋 Tareas Completadas

### 1. ✅ Extensión de Schema Canónico (canonical_schema.py)

**Cambios realizados:**
- Agregado `product` y `expense` a `VALID_DOC_TYPES`
- Creadas nuevas TypedDict:
  - `ProductInfo` - para documentos de tipo producto
  - `ExpenseInfo` - para documentos de tipo gasto
- Actualizado `CanonicalDocument` con campos:
  - `product: Optional[ProductInfo]`
  - `expense: Optional[ExpenseInfo]`
- Agregadas validaciones específicas en `validate_canonical()`:
  - Para `product`: validación de nombre, precio, stock
  - Para `expense`: validación de descripción, monto, fecha, categoría
- Actualizada función `build_routing_proposal()`:
  - Mapeo: `product` → `inventory`
  - Mapeo: `expense` → `expenses`

**Archivos modificados:**
- `app/modules/imports/domain/canonical_schema.py`

---

### 2. ✅ Creación de Validadores Específicos

**Nuevos validadores creados:**

#### a) `validators/expenses.py` (NUEVO)
Funciones:
- `validate_expense(data)` - Validación individual de gasto
- `validate_expenses_batch(items)` - Validación en lote

Valida:
- Descripción (obligatoria, máx 500 chars)
- Monto (obligatorio, > 0)
- Fecha (obligatoria, formato flexible)
- Categoría (opcional, máx 100 chars)
- Método de pago (opcional, lista cerrada)
- Proveedor (opcional, máx 255 chars)
- Número de recibo (opcional)

#### b) `validators/products.py` (YA EXISTENTE)
Funciones:
- `validate_product(data)` - Validación individual de producto
- `validate_products_batch(items)` - Validación en lote

Valida:
- Nombre (obligatorio, máx 255 chars)
- Precio (obligatorio, >= 0)
- Cantidad/Stock (opcional, >= 0)
- Categoría (opcional, máx 200 chars)
- SKU (opcional, máx 100 chars)

**Archivos:**
- `app/modules/imports/validators/expenses.py` (NUEVO)
- `app/modules/imports/validators/products.py` (EXISTENTE)

---

### 3. ✅ Handlers ya existentes

**Handlers actuales soportan:**

#### `InvoiceHandler`
- Promociona facturas a tabla `invoices`
- Crea líneas de factura
- Busca/crea cliente

#### `BankHandler`
- Promociona transacciones bancarias a tabla `bank_transactions`
- Busca/crea cuenta bancaria
- Mapea tipo de movimiento

#### `ExpenseHandler`
- Promociona gastos a tabla `gastos`
- Busca/crea proveedor
- Maneja categoría y método de pago

#### `ProductHandler` (MEJORADO)
- Promociona productos a tabla `products`
- Busca/crea categoría
- Genera SKU automático
- Inicializa stock en almacén

**Archivo:**
- `app/modules/imports/domain/handlers.py`

---

### 4. ✅ Router de Handlers (handlers_router.py)

**Funcionalidades:**
- Mapeo: `doc_type` → Handler class
- Mapeo: `doc_type` → Tabla destino (routing target)
- Método `promote_canonical()` que:
  1. Obtiene handler según `doc_type`
  2. Convierte formato canónico a normalized
  3. Llama método `promote()` del handler
  4. Retorna `PromoteResult`

**Soporta:**
- `invoice` → InvoiceHandler → `invoices`
- `expense_receipt` → ExpenseHandler → `expenses`
- `bank_tx` → BankHandler → `bank_movements`
- `product` → ProductHandler → `products`
- `expense` → ExpenseHandler → `expenses`

**Archivo:**
- `app/modules/imports/domain/handlers_router.py`

---

## 📋 Tareas Pendientes

### 1. ⏳ Garantizar parsers emitan CanonicalDocument válido

**Qué falta:**
- Revisar cada parser (Phase B) para verificar que retorna estructura canónica
- Actualizar parsers si es necesario:
  - `csv_products.py` → debe retornar `doc_type='product'`
  - `xlsx_expenses.py` → debe retornar `doc_type='expense'`
  - `xml_products.py` → debe retornar `doc_type='product'`
  - `pdf_qr.py` → revisión

**Ubicación:**
- `app/modules/imports/parsers/*.py`

**Checklist:**
```
[ ] csv_products.py emite doc_type='product'
[ ] xlsx_expenses.py emite doc_type='expense'
[ ] xml_products.py emite doc_type='product'
[ ] pdf_qr.py emite tipos correctos
[ ] Todos pasan validate_canonical()
```

---

### 2. ⏳ Crear y ejecutar tests

**Tests a crear:**

#### a) Tests de Validación Canónica
```
test_canonical_product_valid()
test_canonical_product_invalid_missing_name()
test_canonical_product_invalid_negative_price()
test_canonical_expense_valid()
test_canonical_expense_invalid_missing_amount()
test_canonical_expense_invalid_date_format()
```

**Ubicación:**
- `tests/modules/imports/test_canonical_schema.py`

#### b) Tests de Validadores
```
test_validate_product_success()
test_validate_product_missing_name()
test_validate_expense_success()
test_validate_expense_invalid_date()
test_validate_products_batch()
test_validate_expenses_batch()
```

**Ubicación:**
- `tests/modules/imports/validators/test_products.py` (EXISTENTE)
- `tests/modules/imports/validators/test_expenses.py` (NUEVO)

#### c) Tests de Handlers
```
test_product_handler_promote_new()
test_product_handler_promote_existing()
test_expense_handler_promote()
test_handlers_router_product()
test_handlers_router_expense()
```

**Ubicación:**
- `tests/modules/imports/test_handlers.py` (EXISTENTE)
- `tests/modules/imports/test_handlers_router.py`

#### d) Tests de Integración
```
test_product_flow_csv_parse_validate_promote()
test_expense_flow_xlsx_parse_validate_promote()
test_mixed_batch_with_products_and_expenses()
```

**Ubicación:**
- `tests/modules/imports/test_integration_phase_c.py` (NUEVO)

---

### 3. ⏳ Actualizar documentación

**Documentos a actualizar:**
- [ ] `README.md` - Agregar sección "Fase C"
- [ ] `CANONICAL_USAGE.md` - Ejemplos de product y expense
- [ ] `GETTING_STARTED_FASE_C.md` - Actualizar con estado actual
- [ ] `HANDLERS_COMPLETOS.md` - Documentar flujo completo

---

## 🏗️ Flujo de Fase C (Detallado)

### Flujo Usuario Final
```
1. Usuario sube archivo (CSV, XLSX, etc)
2. Backend parsea → CanonicalDocument (Fase B)
3. Valida con validate_canonical() (Fase C)
   ├─ ¿Válido? → Continuar
   └─ ¿Inválido? → Guardar errores en ImportItem
4. Obtiene handler según doc_type (Fase C)
5. Handler.promote() inserta en tabla destino (Fase C)
6. Guarda lineage (promoción)
7. Usuario ve resultado: OK o ERROR
```

### Integración Celery
```python
def task_import_file(import_batch_id, parser_id, file_key):
    # 1. Parse (Fase B)
    parser = registry.get_parser(parser_id)
    result = parser['handler'](file_path)  # Retorna items con doc_type

    # 2. Validate (Fase C)
    for item in result['items']:
        is_valid, errors = validate_canonical(item)

        # 3. Promote (Fase C)
        if is_valid:
            handler = HandlersRouter.get_handler_for_type(item['doc_type'])
            promote_result = handler.promote(db, tenant_id, item)
            # Guardar en ImportItem
```

---

## 📚 Referencia de Estructuras

### ProductInfo (CanonicalDocument)
```python
{
    "doc_type": "product",
    "product": {
        "name": "Laptop Dell XPS 13",  # REQUIRED
        "sku": "LAP-0001",             # Optional
        "price": 1200.00,              # REQUIRED
        "stock": 5,                    # Optional, default 0
        "category": "Electrónica",     # Optional
        "unit": "pcs",                 # Optional
        "description": "...",          # Optional
        "supplier": {...},             # Optional
        "barcode": "123456789"         # Optional
    }
}
```

### ExpenseInfo (CanonicalDocument)
```python
{
    "doc_type": "expense",
    "expense": {
        "description": "Combustible gasolina",  # REQUIRED
        "amount": 50.00,                        # REQUIRED
        "expense_date": "2025-11-11",           # REQUIRED
        "category": "combustible",              # Optional
        "payment_method": "cash",               # Optional
        "vendor": {"name": "Estación YPF"},     # Optional
        "receipt_number": "RCP-12345"           # Optional
    }
}
```

---

## 🔗 Links de Referencia

- **canonical_schema.py**: Validaciones y tipos canónicos
- **handlers.py**: Lógica de inserción en tablas destino
- **handlers_router.py**: Despachador de documentos
- **validators/products.py**: Validadores de productos
- **validators/expenses.py**: Validadores de gastos
- **validators/country_validators.py**: Validadores por país
- **GETTING_STARTED_FASE_C.md**: Guía de inicio
- **PARSER_REGISTRY.md**: Registry de parsers (Fase B)

---

## ✅ Checklist de Aprobación para Fase C

### Implementación
- [x] Extender canonical_schema.py con product/expense
- [x] Crear validadores específicos
- [x] Verificar handlers existentes
- [x] Actualizar handlers_router
- [ ] Garantizar parsers emiten CanonicalDocument válido
- [ ] Actualizar models ImportItem para guardar canonical_doc
- [ ] Crear pipeline integrado en Celery

### Testing
- [ ] Tests de validación canónica
- [ ] Tests de validadores (product/expense)
- [ ] Tests de handlers
- [ ] Tests de router
- [ ] Tests de integración E2E

### Documentación
- [ ] README actualizado
- [ ] CANONICAL_USAGE.md con ejemplos
- [ ] Troubleshooting guide
- [ ] API docs

### Preparación para Fase D
- [ ] IA classification endpoints listos
- [ ] modelo de confianza integrado
- [ ] logging de validaciones para iteración

---

## 🚀 Próximos Pasos Inmediatos

1. **Verificar parsers (Fase B)**
   ```bash
   # Ejecutar cada parser y verificar estructura
   python -c "from app.modules.imports.parsers import registry; \
              p = registry.get_parser('csv_products'); \
              result = p['handler']('test.csv'); \
              print(result)"
   ```

2. **Crear tests básicos**
   - Implementar `test_canonical_product_valid()`
   - Implementar `test_canonical_expense_valid()`
   - Ejecutar: `pytest tests/modules/imports/test_canonical_schema.py`

3. **Integrar con Celery**
   - Actualizar `task_import_file()` para usar `validate_canonical()`
   - Agregar lógica de `HandlersRouter.promote_canonical()`

4. **Pasar a Fase D**
   - Una vez tests pasen, iniciar IA configurable
   - Endpoint `/imports/files/classify` debe usar IA local

---

## 📝 Notas de Implementación

### Retrocompatibilidad
- Handlers existentes (`invoice`, `bank_tx`) siguen funcionando
- Nuevos tipos (`product`, `expense`) se agregan sin afectar existentes
- `doc_type='expense'` es diferente de `doc_type='expense_receipt'`
  - `expense`: gasto sencillo
  - `expense_receipt`: recibo formal con líneas

### Validación
- Cada validador retorna `List[str]` con mensajes de error
- `validate_canonical()` retorna `Tuple[bool, List[str]]`
- Errores se guardan en `ImportItem.errors` (JSON)

### Performance
- Validación es O(1) por documento
- Router usa dict lookup, no ciclos
- Batch operations soportadas

---

**Mantenedor**: [DevTeam]
**Estado Actual**: 60% - Continuando con verificación de parsers y tests
