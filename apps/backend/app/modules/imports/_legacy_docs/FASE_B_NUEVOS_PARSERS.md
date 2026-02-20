# Fase B: Nuevos Parsers - Implementación Completada

Documento que documenta los nuevos parsers creados para soportar múltiples formatos de archivos en la Fase B del plan de evolución del importador.

## Parsers Implementados

### 1. CSV Products (`csv_products.py`)
- **Tipo**: Productos
- **Extensión**: .csv
- **Campos esperados**:
  - `name`/`producto`/`nombre` - Nombre del producto (obligatorio)
  - `price`/`precio`/`unit_price` - Precio unitario
  - `quantity`/`cantidad`/`stock` - Cantidad/inventario
  - `sku`/`codigo` - Código único
  - `category`/`categoria` - Categoría (default: "GENERAL")
  - `description`/`descripcion` - Descripción del producto

- **Características**:
  - Detección flexible de columnas (mapeo por keywords)
  - Conversión automática de decimales (`,` → `.`)
  - Limpieza de valores nulos
  - Metadatos de importación

- **Output**: CanonicalDocument con `doc_type='product'`

**Uso**:
```python
from app.modules.imports.parsers import registry

parser_info = registry.get_parser("csv_products")
result = parser_info["handler"]("path/to/products.csv")
# result = {"products": [...], "rows_processed": N, "errors": [...]}
```

---

### 2. XML Products (`xml_products.py`)
- **Tipo**: Productos
- **Extensión**: .xml
- **Estructura esperada**: Elementos anidados con productos
  - Tags detectados: `product`, `producto`, `item`, `article`, `articulo`, `row`, `fila`
  - Campos: name, price, quantity, sku, category, description

- **Características**:
  - Remoción automática de namespaces
  - Búsqueda flexible de elementos
  - Fallback a atributos si no hay elementos hijo
  - Soporte para múltiples variantes de nombres

- **Output**: CanonicalDocument con `doc_type='product'`

**Ejemplo XML válido**:
```xml
<?xml version="1.0"?>
<productos>
  <producto>
    <nombre>Laptop</nombre>
    <precio>1500.00</precio>
    <cantidad>5</cantidad>
    <sku>LAP-001</sku>
    <categoria>Electrónica</categoria>
  </producto>
</products>
```

---

### 3. XLSX Expenses (`xlsx_expenses.py`)
- **Tipo**: Gastos/Recibos
- **Extensión**: .xlsx, .xls
- **Campos esperados**:
  - `date`/`fecha` - Fecha del gasto
  - `description`/`descripcion` - Descripción (obligatorio)
  - `category`/`categoria` - Categoría del gasto
  - `amount`/`monto`/`valor` - Monto (obligatorio)
  - `vendor`/`proveedor` - Proveedor
  - `payment_method`/`forma_pago` - Método de pago
  - `reference`/`referencia` - Referencia/número
  - `tax`/`iva` - Impuesto
  - `currency`/`moneda` - Moneda (default: "USD")

- **Características**:
  - Búsqueda automática de sheets: "GASTOS", "EXPENSES", "RECIBOS", "RECEIPTS"
  - Mapeo flexible de columnas
  - Parseo de fechas
  - Validación: requiere description y amount

- **Output**: CanonicalDocument con `doc_type='expense'`

**Sheet de ejemplo**:
```
| Fecha      | Descripción           | Categoría | Monto  | Proveedor      |
|----------- |---------------------- |---------- |--------|----------------|
| 2025-11-01 | Supplies Office       | Office    | 125.50 | Office Plus    |
| 2025-11-02 | Electricity Bill      | Utilities | 350.00 | Power Company  |
```

---

### 4. PDF QR Code (`pdf_qr.py`)
- **Tipo**: Facturas/Recibos (con QR)
- **Extensión**: .pdf
- **Dependencias**:
  - `pdf2image` - Conversión PDF → imágenes
  - `pyzbar` - Detección de códigos QR

- **Características**:
  - Conversión página a página de PDF a imágenes
  - Extracción de códigos QR de cada página
  - Parseo automático de formatos QR comunes:
    - **Formato pipe-separated**: `RUC|BusinessName|Invoice#|Date|Amount|...`
    - **Formato key=value**: `ruc=VALUE&name=VALUE&invoice=VALUE...`
    - **Formato space-separated**: Fallback simple
  - Mapeo inteligente de campos QR

- **Output**: CanonicalDocument con `doc_type='invoice'` (extraído de QR)

**Instalación de dependencias**:
```bash
pip install pdf2image pyzbar
```

**Ejemplo de QR soportado**:
```
EC1234567890|COMPANY S.A.|INV-2025-001|2025-11-01|500.00|USD
```

---

## Registro en Parser Registry

Todos los parsers están registrados automáticamente en `parsers/__init__.py`:

```python
registry.register(
    "csv_products",
    DocType.PRODUCTS,
    parse_csv_products,
    "CSV parser for product data"
)

registry.register(
    "xml_products",
    DocType.PRODUCTS,
    parse_xml_products,
    "XML parser for product data"
)

registry.register(
    "xlsx_expenses",
    DocType.EXPENSES,
    parse_xlsx_expenses,
    "Excel parser for expense and receipt data"
)

registry.register(
    "pdf_qr",
    DocType.INVOICES,
    parse_pdf_qr,
    "PDF parser with QR code extraction for invoices and receipts"
)
```

## Cómo Usar

### 1. Obtener Parser del Registry
```python
from app.modules.imports.parsers import registry

parser_info = registry.get_parser("csv_products")
if parser_info:
    handler = parser_info["handler"]
    result = handler("path/to/file.csv")
```

### 2. Listar todos los Parsers
```python
all_parsers = registry.list_parsers()
for parser_id, parser_meta in all_parsers.items():
    print(f"{parser_id}: {parser_meta['description']}")
```

### 3. Obtener Parsers por Tipo
```python
from app.modules.imports.parsers import DocType

product_parsers = registry.get_parsers_for_type(DocType.PRODUCTS)
# {
#   "products_excel": {...},
#   "csv_products": {...},
#   "xml_products": {...}
# }
```

## Estructura de Salida

Todos los parsers retornan un dict con esta estructura:

```python
{
    "products": [],  # o "invoices", "expenses", "documents" según tipo
    "rows_processed": int,
    "rows_parsed": int,
    "errors": [],
    "source_type": str,  # "csv", "xlsx", "xml", "pdf"
    "parser": str,  # ID del parser usado
}
```

Cada item contiene:
- `doc_type`: Tipo de documento (product, invoice, expense, etc.)
- Campos específicos del tipo
- `source`: Fuente del parser
- `_metadata`: Información de importación (parser, row/page, timestamp)

## Validación Canónica (Próximo Paso - Fase C)

Después de parsear, cada item debe pasar por:

```python
from app.modules.imports.domain.canonical_schema import validate_canonical

for item in result["products"]:
    canonical_doc = validate_canonical(item)
    if canonical_doc.is_valid():
        # Procesar item válido
        pass
    else:
        # Manejar errores de validación
        print(canonical_doc.errors)
```

## Pruebas

Para probar los nuevos parsers:

```bash
# Test de CSV productos
pytest tests/modules/imports/test_csv_products.py

# Test de XML productos
pytest tests/modules/imports/test_xml_products.py

# Test de XLSX gastos
pytest tests/modules/imports/test_xlsx_expenses.py

# Test de PDF QR
pytest tests/modules/imports/test_pdf_qr.py
```

## Próximos Pasos

- [ ] Fase C: Validación canónica y handlers
  - Extender `canonical_schema.py` para soportar todos los `doc_type`
  - Crear handlers específicos (ProductHandler, ExpenseHandler, etc.)

- [ ] Tests unitarios para cada parser

- [ ] Integración con endpoint `/imports/files/classify`

- [ ] Integración con task Celery `task_import_file`

- [ ] Actualizar documentación y PARSER_REGISTRY.md

## Resumen

✅ **CSV Products** - Importar productos desde archivos CSV
✅ **XML Products** - Importar productos desde XML flexible
✅ **XLSX Expenses** - Importar gastos/recibos desde Excel
✅ **PDF QR** - Extraer facturas/recibos desde PDFs con códigos QR

**Total de parsers disponibles**: 10 (incluyendo existentes)

Los parsers están listos para ser integrados en la Fase C (validación y handlers) y en el flujo Celery.
