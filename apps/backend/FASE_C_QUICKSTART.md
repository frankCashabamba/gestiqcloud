# Fase C - Quick Start

**Tiempo de lectura**: 5 minutos  
**Prerequisitos**: Python 3.9+, database connection

---

## 🎯 TL;DR

Fase C agrega **validación + promoción** al importador:

```
Archivo Excel → Parser → Validación Canónica → Vista Previa → Promoción → BD
                         ↑ NUEVO              ↑ NUEVO                   
```

---

## 1️⃣ Ver el Status Actual

```bash
# Ver qué está completado
cat app/modules/imports/FASE_C_SUMMARY.md

# Ver cómo funciona end-to-end
cat app/modules/imports/FASE_C_INTEGRACION_COMPLETA.md
```

---

## 2️⃣ Ejecutar los Tests

```bash
# Todos los tests de Fase C
pytest tests/modules/imports/test_canonical_schema.py -v
pytest tests/modules/imports/test_promotion.py -v

# Con cobertura
pytest tests/modules/imports/ --cov=app.modules.imports.domain --cov-report=html
```

**Resultado esperado**: ✅ 50+ tests passed

---

## 3️⃣ Usar en Código

### Validar un documento
```python
from app.modules.imports.domain.canonical_schema import validate_canonical

doc = {
    "doc_type": "product",
    "product": {
        "name": "Laptop",
        "price": 1200.0,
        "stock": 5,
    }
}

is_valid, errors = validate_canonical(doc)
if is_valid:
    print("✅ Documento válido")
else:
    print(f"❌ Errores: {errors}")
```

### Promover a tabla destino
```python
from app.modules.imports.domain.handlers_router import HandlersRouter
from app.config.database import session_scope
from uuid import UUID

with session_scope() as db:
    result = HandlersRouter.promote_canonical(
        db=db,
        tenant_id=UUID("12345678-..."),
        canonical_doc=doc,
    )
    
print(f"Promovido a: {result['target']}")
print(f"ID: {result['domain_id']}")
```

---

## 4️⃣ Desde Celery (Asincrónico)

```python
from app.modules.imports.application.tasks.task_promote import promote_batch

# Promocionar todo un batch
task = promote_batch.delay(
    batch_id="abc-123",
    tenant_id="def-456"
)

# Esperar resultado
result = task.get(timeout=30)
print(f"Promovidos: {result['promoted']}")
print(f"Fallidos: {result['failed']}")
```

---

## 5️⃣ Documentación Disponible

| Documento | Propósito |
|-----------|-----------|
| `FASE_C_STATUS.md` | Estado actual y tareas pendientes |
| `FASE_C_SUMMARY.md` | Resumen técnico (350 líneas) |
| `FASE_C_INTEGRACION_COMPLETA.md` | Flujo end-to-end detallado |
| `canonical_schema.py` | Schema con validadores |
| `handlers_router.py` | Despacho dinámico a handlers |
| `handlers.py` | 4 handlers funcionales |
| `test_canonical_schema.py` | 16+ tests de validación |
| `test_promotion.py` | 20+ tests de promoción |

---

## 6️⃣ Archivos Clave

```
app/modules/imports/
├── domain/
│   ├── canonical_schema.py      ← Tipos + validación
│   ├── handlers.py              ← 4 handlers (Invoice, Bank, Expense, Product)
│   └── handlers_router.py       ← Despacho dinámico
│
├── application/tasks/
│   ├── task_import_file.py      ← Integración validate_canonical()
│   └── task_promote.py          ← NUEVO: Promoción a BD
│
└── validators/
    ├── products.py              ← Validadores de producto
    ├── expenses.py              ← Validadores de gasto
    └── country_validators.py    ← Validación por país

tests/modules/imports/
├── test_canonical_schema.py     ← 16+ tests validación
└── test_promotion.py            ← NUEVO: 20+ tests promoción
```

---

## 7️⃣ Tipos Soportados

| doc_type | Target Tabla | Handler | Creado |
|----------|--------------|---------|--------|
| `invoice` | invoices | InvoiceHandler | ✅ Fase A |
| `expense_receipt` | expenses | ExpenseHandler | ✅ Fase A |
| `bank_tx` | bank_movements | BankHandler | ✅ Fase A |
| `product` | inventory | ProductHandler | ✅ Fase C |
| `expense` | expenses | ExpenseHandler | ✅ Fase C |

---

## 8️⃣ Validaciones Incluidas

### Obligatorias (todos)
- ✅ doc_type presente y válido
- ✅ Formatos de fecha YYYY-MM-DD

### Por tipo
- **invoice**: invoice_number, issue_date, vendor
- **product**: product.name, product.price
- **expense**: expense.description, expense.amount, expense_date
- **bank_tx**: bank_tx.amount, bank_tx.direction, bank_tx.value_date

### Integridad
- ✅ Totales cuadran (subtotal + tax = total)
- ✅ Tax breakdown suma correctamente
- ✅ Valores no negativos

---

## 9️⃣ Casos de Uso

### Caso 1: Excel de Productos
```
1. Usuario sube: productos.xlsx
2. Parser detecta: doc_type = "product" (múltiples rows)
3. Validación: Cada producto pasa validate_canonical()
4. Promoción: ProductHandler crea registros en products tabla
5. Resultado: Inventario actualizado
```

### Caso 2: Factura PDF
```
1. Usuario sube: Invoice-2024-001.pdf
2. Parser OCR extrae: doc_type = "invoice"
3. Validación: Fecha, números, totales, vendor
4. Promoción: InvoiceHandler crea en invoices tabla
5. Resultado: Factura registrada para contabilidad
```

### Caso 3: Movimientos Bancarios
```
1. Usuario sube: movimientos.xlsx
2. Parser detecta: doc_type = "bank_tx"
3. Validación: Moneda, dirección, fecha
4. Promoción: BankHandler crea en bank_transactions
5. Resultado: Extracto reconciliado
```

---

## 🔟 Troubleshooting

### Tests fallan: "Module not found"
```bash
# Agregar path
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"
pytest tests/modules/imports/test_promotion.py -v
```

### Validación falla: "Field required"
```python
# Verificar que canonical_doc tenga estructura correcta
print(doc.get("doc_type"))           # Debe existir
print(doc.get("product"))            # Si es product
print(doc.get("expense"))            # Si es expense
```

### Promoción retorna None
```python
# Verificar que handler existe
from app.modules.imports.domain.handlers_router import HandlersRouter
handler = HandlersRouter.get_handler_for_type("product")
assert handler is not None  # Debe existir
```

---

## ✅ Verificar Instalación

```bash
# 1. Imports funcionan
python -c "from app.modules.imports.domain.canonical_schema import validate_canonical; print('✅ canonical_schema OK')"

# 2. Handlers existen
python -c "from app.modules.imports.domain.handlers_router import HandlersRouter; print('✅ handlers_router OK')"

# 3. Tasks existen
python -c "from app.modules.imports.application.tasks.task_promote import promote_batch; print('✅ task_promote OK')"

# 4. Tests corren
pytest tests/modules/imports/test_promotion.py::TestHandlersRouter::test_router_has_handler_for_product -v
```

---

## 🚀 Próximos Pasos

1. **Hoy**: Revisar tests y validar que todo funciona
2. **Mañana**: Integrar con frontend (endpoint para promote)
3. **Próximo sprint**: Fase D - IA configurable

---

## 📞 Referencia Rápida

| Necesito... | Uso esto | Archivo |
|-------------|----------|---------|
| Validar documento | `validate_canonical()` | canonical_schema.py |
| Promover documento | `HandlersRouter.promote_canonical()` | handlers_router.py |
| Promover batch async | `promote_batch.delay()` | task_promote.py |
| Obtener handler | `HandlersRouter.get_handler_for_type()` | handlers_router.py |
| Ver tipos soportados | `HANDLER_MAP.keys()` | handlers_router.py |

---

**Status**: 🟢 LISTO  
**Última actualización**: 11 Nov 2025  
**Autor**: Fase C Implementation
