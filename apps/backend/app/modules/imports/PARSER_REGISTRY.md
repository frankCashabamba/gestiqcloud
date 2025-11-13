# Parser Registry Documentation

## Overview

El registry de parsers centraliza la lista de parsers disponibles para el módulo de importaciones. Cada parser se registra con metadatos que permiten:

1. **Clasificación automática** de archivos por tipo
2. **Despacho dinámico** de tareas Celery
3. **Validación y normalización** a esquema canónico (SPEC-1)

## Parsers Registrados

### Excel (XLSX/XLS)

#### `generic_excel`
- **Tipo**: Genérico
- **Extensiones**: .xlsx, .xls
- **Descripción**: Parser Excel que auto-detecta estructura
- **Salida**: Filas con columnas detectadas

#### `products_excel`
- **Tipo**: Productos
- **Extensiones**: .xlsx, .xls
- **Descripción**: Parser especializado para productos con detección de categoría
- **Salida**: Lista de productos con SKU, precio, stock

### CSV

#### `csv_invoices`
- **Tipo**: Facturas
- **Extensiones**: .csv
- **Descripción**: Parser CSV para facturas/recibos
- **Campos esperados**:
  - invoice_number, issue_date, due_date
  - vendor, vendor_tax_id, vendor_country
  - buyer, buyer_tax_id
  - subtotal, tax, total, currency
  - payment_method
- **Salida**: CanonicalDocument (doc_type='invoice')

#### `csv_bank`
- **Tipo**: Transacciones bancarias
- **Extensiones**: .csv
- **Descripción**: Parser CSV para movimientos bancarios
- **Campos esperados**:
  - transaction_date, value_date
  - amount, direction (debit|credit)
  - narrative, concepto
  - counterparty, iban, reference
- **Salida**: CanonicalDocument (doc_type='bank_tx')

#### `csv_products` (NUEVO)
- **Tipo**: Productos
- **Extensiones**: .csv
- **Descripción**: Parser CSV para datos de productos
- **Campos esperados**:
  - name/producto/nombre (obligatorio)
  - price/precio/unit_price
  - quantity/cantidad/stock
  - sku/codigo
  - category/categoria
  - description/descripcion
- **Salida**: CanonicalDocument (doc_type='product')

### XML

#### `xml_invoice`
- **Tipo**: Facturas
- **Extensiones**: .xml
- **Descripción**: Parser XML para facturas (UBL/CFDI)
- **Soporta**:
  - UBL (Ecuador, España, etc)
  - CFDI (México)
  - Generic XML
- **Salida**: CanonicalDocument (doc_type='invoice')

#### `xml_camt053_bank`
- **Tipo**: Transacciones bancarias
- **Extensiones**: .xml
- **Descripción**: Parser ISO 20022 CAMT.053 para extractos bancarios
- **Estándar**: ISO 20022 technical:xsd:camt.053.001.02
- **Salida**: CanonicalDocument (doc_type='bank_tx')

#### `xml_products` (NUEVO)
- **Tipo**: Productos
- **Extensiones**: .xml
- **Descripción**: Parser XML flexible para datos de productos
- **Elementos soportados**: product, producto, item, article, articulo, row, fila
- **Campos**: name, price, quantity, sku, category, description
- **Características**:
  - Remoción automática de namespaces
  - Detección flexible de elementos
  - Fallback a atributos
- **Salida**: CanonicalDocument (doc_type='product')

### Excel (NUEVO)

#### `xlsx_expenses`
- **Tipo**: Gastos/Recibos
- **Extensiones**: .xlsx, .xls
- **Descripción**: Parser Excel para datos de gastos y recibos
- **Sheets detectados**: GASTOS, EXPENSES, RECIBOS, RECEIPTS (o primera sheet)
- **Campos esperados**:
  - date/fecha
  - description/descripcion (obligatorio)
  - category/categoria
  - amount/monto/valor (obligatorio)
  - vendor/proveedor
  - payment_method/forma_pago
  - reference/referencia
  - tax/iva
  - currency/moneda (default: USD)
- **Salida**: CanonicalDocument (doc_type='expense')

### PDF (NUEVO)

#### `pdf_qr`
- **Tipo**: Facturas/Recibos
- **Extensiones**: .pdf
- **Descripción**: Parser PDF con extracción de códigos QR
- **Dependencias**: pdf2image, pyzbar
- **Formatos QR soportados**:
  - Pipe-separated: `RUC|BusinessName|Invoice#|Date|Amount|...`
  - Key=value: `ruc=VAL&name=VAL&invoice=VAL...`
  - Space-separated: Fallback simple
- **Características**:
  - Conversión página a página de PDF a imágenes
  - Extracción de múltiples QR por página
  - Parseo inteligente de datos QR
- **Salida**: CanonicalDocument (doc_type='invoice')

## Cómo Usar el Registry

### Obtener Parser
```python
from app.modules.imports.parsers import registry

# Por ID
parser = registry.get_parser("csv_invoices")
if parser:
    handler = parser["handler"]
    result = handler(file_path)

# Para un tipo de documento
invoices_parsers = registry.get_parsers_for_type(registry.DocType.INVOICES)
```

### Registrar Nuevo Parser
```python
from app.modules.imports.parsers import registry, DocType

# 1. Crear función parser
def parse_my_format(file_path: str) -> Dict[str, Any]:
    # ... parsing logic
    return {"items": [...], "metadata": {...}}

# 2. Registrarlo
registry.register(
    parser_id="my_custom_parser",
    doc_type=DocType.INVOICES,
    handler=parse_my_format,
    description="Mi parser personalizado"
)
```

## Flujo de Clasificación y Parsing

```
1. Usuario sube archivo
   ↓
2. Endpoint /imports/files/classify
   - FileClassifier analiza extensión y contenido
   - Sugiere parser con confianza
   - Retorna lista de parsers disponibles
   ↓
3. Usuario confirma parser (o acepta sugerencia)
   ↓
4. Celery task: task_import_file(parser_id)
   - Registry obtiene handler del parser
   - Ejecuta parser → resultado normalizado
   - Valida con validate_canonical (SPEC-1)
   - Guarda ImportItems con canonical_doc
   ↓
5. ImportItem con canonical_doc está listo para enrutamiento
```

## Validación y Enrutamiento

Después del parsing:

1. **Validación**: Cada item se valida contra schema SPEC-1
   - Campos obligatorios según doc_type
   - Formatos de fecha, moneda, números
   - Totales cuadran (subtotal + tax = total)
   - País soportado, direcciones válidas

2. **Almacenamiento**: ImportItem incluye:
   - `raw`: Datos originales del archivo
   - `normalized`: Normalizado por parser
   - `canonical_doc`: Documento SPEC-1 validado
   - `status`: OK | ERROR_VALIDATION | ...
   - `errors`: Lista de mensajes de validación

3. **Enrutamiento**: handlers_router mapea doc_type → Handler
   - invoice → InvoiceHandler → tabla invoices
   - bank_tx → BankHandler → tabla bank_transactions
   - expense_receipt → ExpenseHandler → tabla expenses

## IA Gratuita (Local)

El FileClassifier usa:
- **Análisis de extensión**: Rápido, sin IA
- **Análisis de contenido**: Heurísticas basadas en headers/tags
  - Excel: Cuenta keywords en encabezados
  - CSV: Analiza columnas por keywords
  - XML: Detecta namespace (UBL, CFDI, CAMT.053)

**Sin IA pagada**: Funciona 100% local, sin llamadas externas.

## Estado de Implementación

### Completado (Fase B)
✅ csv_products - CSV para productos
✅ xml_products - XML para productos
✅ xlsx_expenses - Excel para gastos
✅ pdf_qr - PDF con extracción de QR

**Total de parsers**: 10 (incluyendo los existentes)

### Próximas Mejoras

- [ ] Fase C: Validación canónica y handlers
- [ ] Soporte PDF con OCR (Tesseract) para facturas sin QR
- [ ] Soporte ODS (OpenDocument Spreadsheet)
- [ ] Parsers específicos por país (España NIF, Perú RUC, México RFC)
- [ ] Detección automática de errores en validación
- [ ] Cache de validaciones
- [ ] Integración con IA para clasificación mejorada
