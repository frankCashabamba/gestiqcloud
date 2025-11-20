# Implementación del Schema Canónico SPEC-1

## Resumen

Se ha implementado el esquema de normalización canónica según SPEC-1 que unifica facturas, recibos y extractos bancarios a un formato estándar extensible.

## Archivos creados

### 1. Schema canónico principal
**`app/modules/imports/domain/canonical_schema.py`** (585 líneas)

Contiene:
- **TypedDict** completo para `CanonicalDocument` y subtipos
- Función `validate_canonical()` con validaciones por doc_type y país
- Funciones `validate_totals()` y `validate_tax_breakdown()`
- `build_routing_proposal()` para sugerir enrutamiento
- Constantes: `VALID_DOC_TYPES`, `VALID_COUNTRIES`, `VALID_CURRENCIES`
- Requiere entradas en formato canónico; las fuentes deben convertir datos heredados antes de invocar el módulo

**Validaciones implementadas:**
- doc_type obligatorio y válido
- Country/currency ISO
- Fechas YYYY-MM-DD
- Totals: subtotal + tax = total (tolerancia 0.01)
- Tax breakdown suma = totals.tax
- Tax ID formato RUC (EC) / NIF-CIF (ES)
- Invoice: requiere invoice_number, issue_date, vendor
- Expense receipt: requiere issue_date, totals.total
- Bank tx: requiere bank_tx.{amount, direction, value_date}

### 2. Extractores actualizados

**`app/modules/imports/extractores/extractor_factura.py`**
- ✅ Emite schema canónico `doc_type="invoice"`
- ✅ Parámetro `country` para adaptación regional
- ✅ Calcula tax_breakdown con tasas por país
- ✅ Genera routing_proposal automático

**`app/modules/imports/extractores/extractor_recibo.py`**
- ✅ Emite schema canónico `doc_type="expense_receipt"`
- ✅ Asume método de pago "cash" por defecto
- ✅ Desglose fiscal con IVA incluido
- ✅ Propuesta de enrutamiento a expenses

**`app/modules/imports/extractores/extractor_banco.py`** (NUEVO)
- ✅ Soporte para **CSV** bancario
- ✅ Soporte para **MT940** (SWIFT)
- ✅ Soporte para **CAMT.053** (ISO 20022 XML)
- ✅ Categorización automática por narrativa (FUEL, UTILITIES, PAYROLL, etc.)
- ✅ Normalización de fechas múltiples formatos
- ✅ Emite `doc_type="bank_tx"` con bloque bank_tx completo

### 3. Validadores actualizados

**`app/modules/imports/validators.py`**
- ✅ Añadido `validate_canonical()` que delega a schema
- ✅ Añadido `validate_totals()` específico
- ✅ Añadido `validate_tax_breakdown()` específico
- ✅ Compatibilidad con validadores existentes (invoices, bank, expenses)

### 4. Tests completos

**`tests/modules/imports/test_canonical_schema.py`** (430+ líneas)

Cobertura:
- ✅ Validación de documentos válidos/inválidos
- ✅ Validación de campos obligatorios por doc_type
- ✅ Validación de países, monedas, fechas
- ✅ Validación de totales y tax_breakdown
- ✅ Conversión legacy → canónico
- ✅ Detección automática de formato
- ✅ Construcción de routing proposals
- ✅ Ejemplos completos (factura EC, transacción bancaria)

### 5. Documentación

**`app/modules/imports/domain/CANONICAL_USAGE.md`**
- Introducción al schema
- Ejemplos por tipo de documento (invoice, receipt, bank_tx)
- Validación paso a paso
- Propuestas de enrutamiento
- Casos de uso completos
- Mejores prácticas

**`app/modules/imports/domain/__init__.py`**
- Exports principales del schema canónico
- Facilita imports: `from app.modules.imports.domain import CanonicalDocument, validate_canonical`

## Características principales

### Extensibilidad
- Todos los campos opcionales excepto `doc_type`
- Campo `metadata` para datos adicionales sin contaminar schema
- `attachments` para vincular archivos relacionados

### Compatibilidad
- El pipeline acepta únicamente documentos que ya cumplan el schema canónico SPEC-1. Los productores deben encargarse de convertir cualquier formato heredado antes de publicar datos.

### Multi-país
- Validación de tax_id según país (RUC Ecuador, NIF/CIF España)
- Tasas de IVA por país (12% EC, 21% ES, 18% PE, 19% CO)
- Monedas correctas por país (USD EC, EUR ES)

### Enrutamiento inteligente
- `routing_proposal` con target, category_code, account, confidence
- Mapeo automático: invoice/expense_receipt → expenses, bank_tx → bank_movements
- Categorización por keywords en narrativa bancaria

### Formatos bancarios soportados
1. **CSV**: flexible, múltiples columnas (fecha/descripción/débito/crédito)
2. **MT940**: formato SWIFT estándar
3. **CAMT.053**: ISO 20022 XML

## Ejemplo de uso completo

```python
# 1. Extracción
from app.modules.imports.extractores.extractor_factura import extraer_factura

texto_ocr = "..."
docs = extraer_factura(texto_ocr, country="EC")
doc = docs[0]

# 2. Validación
from app.modules.imports.domain.canonical_schema import validate_canonical

is_valid, errors = validate_canonical(doc)

if not is_valid:
    print(f"Errores: {errors}")
else:
    # 3. Usar routing_proposal
    proposal = doc["routing_proposal"]
    target = proposal["target"]  # "expenses"

    # 4. Publicar a tabla destino
    # ... crear registro en expenses con totals, lines, vendor
```

## Próximos pasos (sugeridos)

1. **Integración con pipeline existente** (`job_runner`, `ImportItem`)
   - Guardar schema canónico en `import_items.normalized` (JSONB)
   - Usar `validate_canonical()` en fase VALIDATED
   - Generar routing_proposal automáticamente

2. **Tabla `import_routing_decisions`**
   - Almacenar propuestas (proposed/confirmed/overridden)
   - Endpoints `GET /proposal` y `POST /route`

3. **Publisher idempotente**
   - Upsert a `expenses/incomes/bank_movements` con `source_item_id`
   - Registrar `import_lineage`

4. **Extractores adicionales**
   - XML (Facturae, UBL 2.3)
   - Excel/XLSX (configurable por mappings)
   - QR codes (clave de acceso SRI)

5. **Validadores por país** (plugins)
   - Reglas SRI (Ecuador): clave de acceso, secuencialidad
   - Reglas SII (España): NIF/CIF, formato de series

6. **Integración Copiloto**
   - Q&A sobre documentos importados (schema canónico)
   - Sugerencias de categorización/enrutamiento

## Testing

Ejecutar tests:
```bash
pytest apps/backend/tests/modules/imports/test_canonical_schema.py -v
```

Tests incluidos:
- 15+ test cases de validación
- Ejemplos de documentos válidos (factura EC, bank tx)
- Validaciones de totales y tax_breakdown

## Compatibilidad

✅ Compatible con extractores existentes (extractor_desconocido, extractor_transferencia)
✅ Compatible con validadores (validate_invoices, validate_bank, validate_expenses)
✅ Preparado para RLS multi-tenant (tenant_id en tablas destino)

## Resumen de constantes

```python
VALID_DOC_TYPES = ["invoice", "expense_receipt", "bank_tx", "other"]
VALID_COUNTRIES = ["EC", "ES", "PE", "CO", "MX", "US"]
VALID_CURRENCIES = ["USD", "EUR", "PEN", "COP", "MXN"]
VALID_DIRECTIONS = ["debit", "credit"]
VALID_PAYMENT_METHODS = ["cash", "card", "transfer", "check", "other"]
VALID_ROUTING_TARGETS = ["expenses", "income", "bank_movements"]
```

## Notas técnicas

- **Tolerancia de redondeo**: 0.01 en validación de totales
- **Fechas**: siempre YYYY-MM-DD (ISO 8601)
- **Tax IDs**: validación básica formato, extensible por país
- **Confidence**: float [0..1] para tracking de calidad OCR/extracción
- **Source**: ocr|xml|csv|api para trazabilidad

---

**Implementado por**: Amp (Sourcegraph AI)
**Fecha**: 2025-01-17
**Basado en**: SPEC-1 Importador documental GestiqCloud
