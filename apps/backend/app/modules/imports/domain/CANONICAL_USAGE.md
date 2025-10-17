# Schema Canónico SPEC-1 — Guía de Uso

## Introducción

El schema canónico unifica todos los tipos de documentos (facturas, recibos, extractos bancarios) a un formato estándar JSON que facilita:

- **Validación** consistente con reglas por país (EC/ES)
- **Enrutamiento** automático a tablas destino (expenses/income/bank_movements)
- **Extensibilidad** sin cambiar modelo core
- **Compatibilidad** hacia atrás con formato legacy

## Estructura básica

```python
from app.modules.imports.domain.canonical_schema import CanonicalDocument

doc: CanonicalDocument = {
    "doc_type": "invoice",  # invoice|expense_receipt|bank_tx|other
    "country": "EC",        # ISO 3166-1 alpha-2
    "currency": "USD",      # ISO 4217
    "issue_date": "2025-01-15",
    "vendor": {...},
    "totals": {...},
    "lines": [...],
    "routing_proposal": {...}
}
```

## Ejemplos por tipo de documento

### 1. Factura (Invoice)

```python
from app.modules.imports.extractores.extractor_factura import extraer_factura

texto_ocr = """
FACTURA 001-002-000123
Fecha: 15/01/2025
Proveedor: Suministros SA
RUC: 1792012345001

Suministros de oficina    $100.00
IVA 12%                   $ 12.00
TOTAL                     $112.00
"""

# Extractor retorna schema canónico
documentos = extraer_factura(texto_ocr, country="EC")
doc = documentos[0]

print(doc["doc_type"])  # "invoice"
print(doc["totals"]["total"])  # 112.0
print(doc["vendor"]["tax_id"])  # "1792012345001"
```

### 2. Recibo/Ticket (Expense Receipt)

```python
from app.modules.imports.extractores.extractor_recibo import extraer_recibo

texto_ocr = """
TICKET DE COMPRA
Fecha: 15/01/2025
Gasolina Super    $50.00
"""

documentos = extraer_recibo(texto_ocr, country="EC")
doc = documentos[0]

print(doc["doc_type"])  # "expense_receipt"
print(doc["payment"]["method"])  # "cash"
print(doc["routing_proposal"]["category_code"])  # "OTROS"
```

### 3. Extracto Bancario (Bank Transaction)

```python
from app.modules.imports.extractores.extractor_banco import extraer_banco_csv

csv_content = """
fecha,descripcion,referencia,debito,credito,saldo
2025-01-15,Transferencia recibida,TRX123,,1500.00,5500.00
2025-01-16,Pago servicios,SRV456,120.00,,5380.00
"""

documentos = extraer_banco_csv(csv_content, country="EC")

for doc in documentos:
    print(f"{doc['bank_tx']['direction']}: ${doc['bank_tx']['amount']}")
    # Output:
    # credit: $1500.0
    # debit: $120.0
```

## Validación

```python
from app.modules.imports.domain.canonical_schema import validate_canonical

doc = {
    "doc_type": "invoice",
    "country": "EC",
    "currency": "USD",
    "issue_date": "2025-01-15",
    "invoice_number": "001-002-000123",
    "vendor": {"name": "Proveedor SA", "tax_id": "1792012345001"},
    "totals": {"subtotal": 100.0, "tax": 12.0, "total": 112.0}
}

is_valid, errors = validate_canonical(doc)

if is_valid:
    print("✅ Documento válido")
else:
    for error in errors:
        print(f"❌ {error}")
```

### Validaciones incluidas

- **doc_type**: obligatorio, valores válidos
- **country**: código ISO 3166-1 alpha-2
- **currency**: código ISO 4217
- **fechas**: formato YYYY-MM-DD
- **totals**: subtotal + tax = total (tolerancia 0.01)
- **tax_breakdown**: suma = totals.tax
- **tax_id**: formato RUC (EC) / NIF-CIF (ES)
- **invoice_number**: obligatorio para facturas
- **bank_tx**: amount, direction, value_date obligatorios

## Conversión desde formato legacy

```python
from app.modules.imports.domain.canonical_schema import convert_legacy_to_canonical

# Formato antiguo (DocumentoProcesado)
legacy = {
    "fecha": "2025-01-15",
    "concepto": "Compra suministros",
    "importe": 112.0,
    "documentoTipo": "factura",
    "invoice": "001-002-000123",
    "cliente": "Proveedor ABC",
    "origen": "ocr"
}

# Convertir a canónico
canonical = convert_legacy_to_canonical(legacy)

print(canonical["doc_type"])  # "invoice"
print(canonical["totals"]["total"])  # 112.0
```

### Detección automática

```python
from app.modules.imports.domain.canonical_schema import detect_and_convert

# Detecta automáticamente si es legacy o canónico
data = {"fecha": "2025-01-15", "documentoTipo": "factura", ...}
canonical = detect_and_convert(data)  # Convierte si es legacy

data2 = {"doc_type": "invoice", "issue_date": "2025-01-15", ...}
canonical2 = detect_and_convert(data2)  # No convierte, ya es canónico
```

## Propuestas de enrutamiento

```python
from app.modules.imports.domain.canonical_schema import build_routing_proposal

doc = {
    "doc_type": "invoice",
    "totals": {"total": 150.0}
}

# Construir propuesta
proposal = build_routing_proposal(
    doc,
    category_code="FUEL",
    account="6230",  # Cuenta PGC/PUC
    confidence=0.85
)

print(proposal)
# {
#     "target": "expenses",
#     "category_code": "FUEL",
#     "account": "6230",
#     "confidence": 0.85
# }
```

### Mapeo automático de targets

| doc_type | target (default) |
|----------|------------------|
| invoice  | expenses         |
| expense_receipt | expenses  |
| bank_tx  | bank_movements   |
| other    | expenses         |

## Integración con validadores

```python
from app.modules.imports.validators import validate_canonical, validate_totals

# Validación completa
errors = validate_canonical(doc)

# Validación específica de totales
totals = doc.get("totals")
totals_errors = validate_totals(totals)

if totals_errors:
    for err in totals_errors:
        print(f"{err['field']}: {err['msg']}")
```

## Extensibilidad

### Añadir campos personalizados

```python
doc: CanonicalDocument = {
    "doc_type": "invoice",
    # ... campos estándar ...
    "metadata": {
        "custom_field_1": "valor personalizado",
        "internal_id": 12345,
        "processing_notes": "Requiere aprobación gerencia"
    }
}
```

### Añadir attachments

```python
doc["attachments"] = [
    {
        "file_key": "s3://bucket/invoices/2025/01/invoice_123.pdf",
        "mime": "application/pdf",
        "type": "original",
        "pages": 2,
        "size": 245678
    },
    {
        "file_key": "s3://bucket/thumbs/invoice_123_thumb.jpg",
        "mime": "image/jpeg",
        "type": "thumbnail"
    }
]
```

## Desglose fiscal avanzado

```python
doc["totals"] = {
    "subtotal": 150.0,
    "tax": 21.0,
    "total": 171.0,
    "discount": 10.0,
    "withholding": 3.0,
    "tax_breakdown": [
        {
            "code": "IVA12-EC",
            "rate": 12.0,
            "amount": 18.0,
            "base": 150.0
        },
        {
            "code": "ICE20-EC",
            "rate": 20.0,
            "amount": 3.0,
            "base": 15.0
        }
    ]
}
```

## Casos de uso completos

### Flujo: Carga → Extracción → Validación → Enrutamiento

```python
from app.modules.imports.extractores.extractor_factura import extraer_factura
from app.modules.imports.domain.canonical_schema import validate_canonical
from app.modules.imports.validators import validate_canonical as validate_errors

# 1. Extracción (OCR → Canónico)
texto_ocr = "..."  # Texto extraído del PDF/imagen
docs = extraer_factura(texto_ocr, country="EC")
doc = docs[0]

# 2. Validación
is_valid, validation_errors = validate_canonical(doc)

if not is_valid:
    # Guardar errores en import_items.errors
    errors_json = [{"field": "general", "msg": err} for err in validation_errors]
    # item.errors = errors_json
    # item.status = "VALIDATED_FAIL"
else:
    # 3. Enrutamiento (usar routing_proposal)
    proposal = doc["routing_proposal"]
    target = proposal["target"]  # "expenses"|"income"|"bank_movements"
    
    # 4. Publicar a tabla destino
    if target == "expenses":
        expense = create_expense_from_canonical(doc, tenant_id)
        # ... guardar en BD
```

## Países soportados

| Código | País    | Moneda | IVA default |
|--------|---------|--------|-------------|
| EC     | Ecuador | USD    | 12%         |
| ES     | España  | EUR    | 21%         |
| PE     | Perú    | PEN    | 18%         |
| CO     | Colombia| COP    | 19%         |

## Constantes útiles

```python
from app.modules.imports.domain.canonical_schema import (
    VALID_DOC_TYPES,
    VALID_COUNTRIES,
    VALID_CURRENCIES,
    VALID_DIRECTIONS,
    VALID_PAYMENT_METHODS,
    VALID_ROUTING_TARGETS
)

print(VALID_DOC_TYPES)
# ['invoice', 'expense_receipt', 'bank_tx', 'other']

print(VALID_COUNTRIES)
# frozenset({'EC', 'ES', 'PE', 'CO', 'MX', 'US'})
```

## Mejores prácticas

1. **Siempre valida** después de construir un documento
2. **Usa detect_and_convert** para manejar legacy y canónico transparentemente
3. **Añade confidence** para tracking de calidad
4. **Rellena metadata** con información adicional sin contaminar campos core
5. **Construye routing_proposal** basado en reglas del negocio
6. **Tolerancia de redondeo**: 0.01 en totales

## Referencias

- SPEC-1: `/apps/backend/app/modules/imports/spec_1_importador_documental_gestiq_cloud.md`
- Tests: `/apps/backend/tests/modules/imports/test_canonical_schema.py`
- Extractores: `/apps/backend/app/modules/imports/extractores/`
