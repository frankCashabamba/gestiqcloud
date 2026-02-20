# P0 Implementation Summary

## Overview
Implementación de 3 objetivos críticos P0 para esta semana:

1. **Imports canónico v1** - Definir contratos por tipo documental
2. **Parser Excel robusto único** - Unificar detección header + limpieza
3. **Errores estructurados por fila/campo** - Respuestas detalladas con contexto

## 1. Canonical Schema v1

**Archivo:** `apps/backend/app/modules/imports/domain/canonical_schema.py`

Define tipos documentales con campos obligatorios y validadores:

- **SALES_INVOICE**: factura de venta (cliente, fecha, total, tax_id)
- **PURCHASE_INVOICE**: factura de compra (proveedor, fecha, total)
- **EXPENSE**: gasto (fecha, concepto, monto, categoría)
- **BANK_TX**: transacción bancaria (fecha, monto, descripción)

### Características

```python
from app.modules.imports.domain import (
    get_schema,
    SALES_INVOICE_SCHEMA,
    DocumentType,
)

schema = get_schema("sales_invoice")
schema.fields["invoice_number"]  # CanonicalField
schema.fields["invoice_number"].aliases  # ["factura", "invoice", "numero", ...]
schema.fields["invoice_number"].rules  # [FieldRule(...)]
```

- **Campos canónicos** con nombres estandarizados
- **Aliases** para detectar mapeos (factura = invoice_number)
- **Reglas de validación** (required, number, positive, date, tax_id)
- **Tipos de datos** (string, number, date, decimal)

## 2. Errores Estructurados

**Archivo:** `apps/backend/app/modules/imports/domain/errors.py`

Reemplaza respuestas genéricas "Bad Request" con errores contextuales:

```python
from app.modules.imports.domain import ImportError, ImportErrorCollection

error = ImportError(
    row_number=42,           # Ubicación en archivo
    field_name="amount",     # Campo source
    canonical_field="amount_total",  # Campo canónico
    category=ErrorCategory.VALIDATION,
    severity=ErrorSeverity.ERROR,
    rule_name="is_positive",  # Qué regla falló
    message="Amount must be positive",
    suggestion="Ensure the value is > 0",
    raw_value="-100.00",  # Valor que falló
)

# Serializar
error.to_dict()  # {"row_number": 42, "field_name": "amount", ...}

# Coleccionar y agrupar
errors = ImportErrorCollection()
errors.add(...)
errors.by_row()      # {42: [ImportError, ...], 43: [...]}
errors.by_field()    # {"amount": [...], "invoice_date": [...]}
```

### Categorías de error

- **VALIDATION** - Regla de validación fallida
- **TYPE_MISMATCH** - Tipo de dato incorrecto
- **MISSING_FIELD** - Campo obligatorio ausente
- **PARSING** - Error al parsear archivo
- **DUPLICATE** - Fila duplicada
- **RANGE_VIOLATION** - Fuera de rango
- **FORMAT** - Formato incorrecto
- **CUSTOM** - Error personalizado

## 3. Validador Universal

**Archivo:** `apps/backend/app/modules/imports/domain/validator.py`

Valida documentos contra schemas canónicos y detecta mappeos:

```python
from app.modules.imports.domain import universal_validator

# Validación
is_valid, errors = universal_validator.validate_document_complete(
    data={"invoice_number": "INV-001", "invoice_date": "2024-01-15", ...},
    doc_type="sales_invoice",
    row_number=42,
    item_id="item-123",
    batch_id="batch-456",
)

# Auto-detectar mapeo de headers
headers = ["Numero de Factura", "Fecha", "Cliente", "Total"]
mapping = universal_validator.find_field_mapping(headers, "sales_invoice")
# -> {"Numero de Factura": "invoice_number", "Fecha": "invoice_date", ...}
```

### Características

- **Validación completa** contra schema
- **Mensajes de error** contextualizados
- **Sugerencias de fix** automáticas
- **Field mapping fuzzy** (busca keywords en aliases)
- **Trazabilidad** (row, field, rule, item_id, batch_id)

## 4. Parser Excel Robusto

**Archivo:** `apps/backend/app/modules/imports/parsers/robust_excel.py`

Unifica detección header + limpieza de filas junk:

```python
from app.modules.imports.parsers.robust_excel import robust_parser

# Análisis (igual header detection que parse)
analysis = robust_parser.analyze_file("file.xlsx")
# -> {"headers": [...], "header_row": 2, "sample_rows": [...], ...}

# Parse completo
result = robust_parser.parse_file("file.xlsx")
# -> {"headers": [...], "rows": [{header: value, ...}, ...], "errors": [...]}
```

### Características

- **Header detection** automática (ignora instrucciones/notas)
- **Junk row cleanup** (filas con palabras clave de instrucciones)
- **Normalización** de espacios/valores vacíos
- **Manejo de merged cells** y formatos rotos
- **Misma lógica en analyze + parse** (garantiza consistencia)

### Palabras clave de "basura"

Detecta y omite filas que contengan:
- instrucciones, como, rellenar, completar
- nota, notas, aviso, observaciones
- ejemplo, guia, ayuda
- etc.

## Integración en Pipeline

### 1. Analyze (SmartRouter)

```python
from app.modules.imports.services.smart_router import smart_router

result = await smart_router.analyze_file(
    file_path="...",
    filename="1b8408...xls",
    tenant_id="...",
)

# Ahora incluye header_row, headers, sample_rows con mismo parser
```

### 2. Parse + Validate

```python
# Parse con robust_excel
parse_result = robust_parser.parse_file("...")
for row_idx, row_data in enumerate(parse_result["rows"], start=1):
    # Validar cada fila
    is_valid, errors = universal_validator.validate_document_complete(
        data=row_data,
        doc_type="sales_invoice",
        row_number=row_idx,
        item_id=item.id,
        batch_id=batch.id,
    )

    if not is_valid:
        # Errores con contexto completo
        for error in errors:
            print(f"Row {error.row_number}, Field {error.field_name}: {error.message}")
            print(f"  Suggestion: {error.suggestion}")
```

### 3. API Response

```json
{
  "batch_id": "...",
  "status": "VALIDATION_FAILED",
  "errors": [
    {
      "row_number": 42,
      "field_name": "amount",
      "canonical_field": "amount_total",
      "category": "validation",
      "severity": "error",
      "rule_name": "is_positive",
      "message": "Amount must be positive",
      "suggestion": "Ensure value > 0",
      "raw_value": "-100.00",
      "item_id": "item-456",
      "doc_type": "sales_invoice"
    }
  ]
}
```

## Archivos Creados/Modificados

### Nuevos
- `apps/backend/app/modules/imports/domain/canonical_schema.py` (425 líneas)
- `apps/backend/app/modules/imports/domain/errors.py` (215 líneas)
- `apps/backend/app/modules/imports/domain/validator.py` (195 líneas)
- `apps/backend/app/modules/imports/parsers/robust_excel.py` (310 líneas)
- `apps/backend/app/tests/test_imports_p0_canonical.py` (438 líneas)

### Modificados
- `apps/backend/app/modules/imports/domain/__init__.py` - Actualizar imports

## Tests

**Archivo:** `apps/backend/app/tests/test_imports_p0_canonical.py`

Cubre:
- ✓ Retrieval de schemas
- ✓ Estructura de errores
- ✓ Validación de documentos (válidos + inválidos)
- ✓ Detección de field mapping
- ✓ Error grouping (by row, field, category)

Ejecutar:
```bash
python -m pytest apps/backend/app/tests/test_imports_p0_canonical.py -v
```

## Próximos Pasos (P1)

1. Integrar robust_excel en SmartRouter.analyze_file
2. Integrar universal_validator en parse pipeline
3. Actualizar endpoints HTTP para retornar structured errors
4. Auto-learning de mappings (feedback.py)
5. Confirmación obligatoria por baja confianza

## Criterios P0 Completados

- ✅ Cada tipo (sales_invoice, purchase_invoice, expense, bank_tx) con obligatorios y validadores
- ✅ Parser Excel unificado: misma detección header en analyze + parse
- ✅ Errores estructurados: row, field, rule, message, suggestion
- ✅ Suite de regresión básica (puede expandirse con archivos reales)
