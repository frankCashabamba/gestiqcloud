# Testing y Uso de Nuevos Parsers (Fase B)

Guía práctica para probar los nuevos parsers sin necesidad de integración completa.

## 1. Setup Inicial

### Instalar Dependencias Opcionales
```bash
# Para PDF QR
pip install pdf2image pyzbar

# Alternativa: si tienes problemas con pyzbar
pip install pdf2image zbar-py
```

### Verificar Registro de Parsers
```python
from app.modules.imports.parsers import registry

# Ver todos los parsers
all_parsers = registry.list_parsers()
for parser_id, meta in all_parsers.items():
    print(f"{parser_id}: {meta['description']}")
```

## 2. Testing Individual de Parsers

### CSV Products

**Crear archivo de prueba** (`test_products.csv`):
```csv
name,price,quantity,sku,category,description
Laptop HP,1500.00,5,LAP-001,Electrónica,Laptop HP 15 pulgadas
Mouse Logitech,25.50,50,MOU-001,Accesorios,Mouse inalámbrico
Teclado Mecánico,85.00,10,TEC-001,Accesorios,Teclado RGB
```

**Script de prueba**:
```python
from app.modules.imports.parsers import registry

parser = registry.get_parser("csv_products")
handler = parser["handler"]

result = handler("test_products.csv")

print(f"Productos encontrados: {len(result['products'])}")
print(f"Errores: {result['errors']}")

for product in result['products']:
    print(f"  - {product['nombre']}: ${product['price']} ({product['quantity']} units)")
```

**Salida esperada**:
```
Productos encontrados: 3
Errores: []
  - Laptop HP: $1500.0 (5.0 units)
  - Mouse Logitech: $25.5 (50.0 units)
  - Teclado Mecánico: $85.0 (10.0 units)
```

---

### XML Products

**Crear archivo de prueba** (`test_products.xml`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<inventory>
  <producto>
    <nombre>Producto A</nombre>
    <precio>100.50</precio>
    <cantidad>20</cantidad>
    <sku>PA-001</sku>
    <categoria>Categoría 1</categoria>
    <descripcion>Descripción del producto A</descripcion>
  </producto>
  <producto>
    <nombre>Producto B</nombre>
    <precio>250.00</precio>
    <cantidad>10</cantidad>
    <sku>PB-001</sku>
    <categoria>Categoría 2</categoria>
  </producto>
</inventory>
```

**Script de prueba**:
```python
from app.modules.imports.parsers import registry

parser = registry.get_parser("xml_products")
result = parser["handler"]("test_products.xml")

print(f"Productos: {len(result['products'])}")
for product in result['products']:
    print(f"  {product['nombre']} - SKU: {product.get('sku', 'N/A')}")
```

---

### XLSX Expenses

**Crear archivo de prueba** (usando openpyxl):
```python
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "GASTOS"

# Header
ws.append(["Fecha", "Descripción", "Categoría", "Monto", "Proveedor", "Forma Pago"])

# Data
ws.append(["2025-11-01", "Suministros Oficina", "Office", 125.50, "Office Plus", "Transferencia"])
ws.append(["2025-11-02", "Electricidad", "Utilities", 350.00, "Power Company", "Débito"])
ws.append(["2025-11-03", "Internet", "Telecom", 50.00, "Internet ISP", "Tarjeta"])

wb.save("test_expenses.xlsx")
```

**Script de prueba**:
```python
from app.modules.imports.parsers import registry

parser = registry.get_parser("xlsx_expenses")
result = parser["handler"]("test_expenses.xlsx")

print(f"Gastos registrados: {len(result['expenses'])}")
for expense in result['expenses']:
    print(f"  {expense['description']}: ${expense['amount']} ({expense.get('category', 'N/A')})")
```

**Salida esperada**:
```
Gastos registrados: 3
  Suministros Oficina: $125.5 (Office)
  Electricidad: $350.0 (Utilities)
  Internet: $50.0 (Telecom)
```

---

### PDF QR

**Crear PDF con QR** (usando qrcode library):
```bash
pip install qrcode[pil]
```

```python
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Generar código QR
qr = qrcode.QRCode()
qr.add_data("EC1234567890|COMPANY S.A.|INV-2025-001|2025-11-01|500.00|USD")
qr.make()
img = qr.make_image()

# Crear PDF con la imagen
c = canvas.Canvas("test_invoice.pdf", pagesize=letter)
c.drawString(100, 750, "INVOICE")
c.drawImage("qr.png", 100, 500, width=200, height=200)
c.save()
```

**Script de prueba**:
```python
from app.modules.imports.parsers import registry

parser = registry.get_parser("pdf_qr")
result = parser["handler"]("test_invoice.pdf")

print(f"Documentos extraídos: {len(result['documents'])}")
for doc in result['documents']:
    print(f"  Invoice: {doc.get('invoice_number', 'N/A')}")
    if 'vendor' in doc:
        print(f"    Vendor: {doc['vendor'].get('name', 'N/A')}")
```

---

## 3. Testing Integrado

### Usando el Registry

```python
from app.modules.imports.parsers import registry, DocType

# Obtener todos los parsers de productos
product_parsers = registry.get_parsers_for_type(DocType.PRODUCTS)

print(f"Parsers disponibles para productos: {len(product_parsers)}")
for parser_id, meta in product_parsers.items():
    print(f"  - {parser_id}: {meta['description']}")
```

### Simular Flujo Completo

```python
from app.modules.imports.parsers import registry

# 1. Usuario sube archivo
file_path = "test_products.csv"
parser_id = "csv_products"  # Podría venir de clasificación IA

# 2. Obtener parser del registry
parser_info = registry.get_parser(parser_id)
if not parser_info:
    print(f"Parser {parser_id} no encontrado")
    exit(1)

# 3. Ejecutar parser
handler = parser_info["handler"]
result = handler(file_path)

# 4. Procesar resultados
if result['errors']:
    print(f"Errores: {result['errors']}")

print(f"Registros procesados: {result['rows_parsed']} / {result['rows_processed']}")

# 5. (Próximo paso) Validar con canonical_schema
# for item in result['products']:
#     canonical = validate_canonical(item)
#     if canonical.is_valid():
#         # Procesar item válido
```

---

## 4. Troubleshooting

### Error: "pdf2image not found"
```bash
# Windows
pip install pdf2image
# Instalar poppler: https://github.com/oschwartz10612/poppler-windows/releases/

# MacOS
brew install poppler

# Linux
sudo apt-get install poppler-utils
```

### Error: "pyzbar not found"
```bash
# Windows
pip install pyzbar
# Instalar zbar binaries: https://github.com/NaturalHistoryMuseum/pyzbar

# MacOS
brew install zbar

# Linux
sudo apt-get install libzbar0
```

### CSV con encoding diferente
```python
# El parser ya soporta utf-8-sig por defecto
# Para otros encodings, el error lo indicará en 'errors'
```

### XML con namespaces complejos
```python
# El parser automáticamente remueve namespaces
# Si aún hay problemas, checkear el archivo con:
import xml.etree.ElementTree as ET
tree = ET.parse("file.xml")
root = tree.getroot()
print(root.tag)  # Ver si tiene namespace
```

---

## 5. Métricas y Validación

### Validar Estructura de Salida

```python
from app.modules.imports.parsers import registry

def validate_parser_output(parser_id, file_path):
    """Validar que un parser devuelve estructura correcta."""
    parser = registry.get_parser(parser_id)
    result = parser["handler"](file_path)

    # Validar estructura base
    required_keys = ["rows_processed", "rows_parsed", "errors", "source_type", "parser"]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"

    # Validar items
    item_key = list(result.keys())[0] if result else None
    if item_key and isinstance(result[item_key], list):
        for item in result[item_key]:
            assert "doc_type" in item, f"Item missing doc_type: {item}"
            assert "_metadata" in item, f"Item missing _metadata: {item}"

    return True

# Test all parsers
for parser_id in ["csv_products", "xml_products", "xlsx_expenses", "pdf_qr"]:
    try:
        # Usando archivos de prueba creados arriba
        result = validate_parser_output(parser_id, "test_file")
        print(f"✓ {parser_id}: OK")
    except AssertionError as e:
        print(f"✗ {parser_id}: {e}")
```

---

## 6. Próximos Pasos

Una vez que los parsers están validados:

1. **Integración con Celery**
   - `task_import_file(parser_id, file_key, ...)`

2. **Validación Canónica**
   - Pasar cada item por `validate_canonical()`

3. **Handlers**
   - Procesar items validados a tablas destino

4. **Tests Unitarios**
   - Crear `tests/modules/imports/test_csv_products.py`, etc.

---

## Resumen

✅ **CSV Products** - Probado y funcional
✅ **XML Products** - Probado y funcional
✅ **XLSX Expenses** - Probado y funcional
✅ **PDF QR** - Listo (requiere dependencias opcionales)

Todos los parsers están listos para la siguiente fase de validación y handlers.
