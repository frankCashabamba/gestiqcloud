# Parser Registry - Guía de Extensión

**Fecha:** 11 Nov 2025
**Versión:** 1.0.0

---

## 1. Introducción

El **Parser Registry** permite registrar nuevos parsers dinámicamente sin modificar código. Cada parser puede manejar un formato específico (CSV, Excel, XML, PDF, etc.) y transformarlo a `CanonicalDocument`.

---

## 2. Estructura del Registry

### Ubicación
```
app/modules/imports/parsers/
├── __init__.py              # Registry principal
├── base.py                  # ParserBase (interface)
├── csv_products.py
├── csv_invoices.py
├── xml_products.py
├── xml_invoice.py
├── xml_camt053_bank.py
├── xlsx_expenses.py
└── pdf_qr.py
```

### Registry Interface

```python
# app/modules/imports/parsers/__init__.py

class ParserRegistry:
    """Registry centralizado de parsers."""

    def register(self, parser_id: str, parser_class: Type[ParserBase],
                 metadata: ParserMetadata) -> None:
        """Registrar un parser nuevo."""

    def get(self, parser_id: str) -> Optional[ParserBase]:
        """Obtener instancia de parser por ID."""

    def list(self) -> List[ParserMetadata]:
        """Listar todos los parsers disponibles."""

    def get_by_doc_type(self, doc_type: str) -> List[ParserBase]:
        """Obtener parsers para un doc_type específico."""
```

---

## 3. Crear un Parser Nuevo

### Paso 1: Crear archivo del parser

**Archivo:** `app/modules/imports/parsers/my_custom_parser.py`

```python
"""Custom parser para formato específico."""

from typing import List, Dict, Any
from .base import ParserBase
from ..domain.canonical_schema import CanonicalDocument, CanonicalItem

class MyCustomParser(ParserBase):
    """Parser para formato personalizado."""

    PARSER_ID = "my_custom_format"
    DOC_TYPE = "invoice"  # invoice, expense, product, bank_tx, etc.
    SUPPORTED_EXTENSIONS = [".custom", ".txt"]

    async def parse(self, file_path: str, **kwargs) -> CanonicalDocument:
        """
        Parsear archivo y retornar CanonicalDocument.

        Args:
            file_path: Ruta al archivo
            **kwargs: Opciones adicionales (tenant_id, user_id, etc.)

        Returns:
            CanonicalDocument con items parseados
        """
        # 1. Leer archivo
        with open(file_path, 'r') as f:
            content = f.read()

        # 2. Parsear contenido
        items = self._parse_content(content)

        # 3. Construir CanonicalDocument
        doc = CanonicalDocument(
            doc_type=self.DOC_TYPE,
            parser_id=self.PARSER_ID,
            source_file=Path(file_path).name,
            items=items,
            metadata={"format": "custom"}
        )

        return doc

    def _parse_content(self, content: str) -> List[CanonicalItem]:
        """Parsear contenido específico."""
        items = []
        # Lógica de parsing
        return items

    def validate(self, item: CanonicalItem) -> bool:
        """Validar item parseado."""
        return True
```

### Paso 2: Registrar el parser

**Archivo:** `app/modules/imports/parsers/__init__.py`

```python
# Al final del archivo, después de la clase ParserRegistry

from .my_custom_parser import MyCustomParser

# Registrar
registry.register(
    parser_id="my_custom_format",
    parser_class=MyCustomParser,
    metadata=ParserMetadata(
        id="my_custom_format",
        doc_type="invoice",
        handler="expense_handler",
        extensions=[".custom", ".txt"],
        description="Parser para formato personalizado",
        version="1.0.0"
    )
)
```

### Paso 3: Verificar

```python
# En código o tests
parser = registry.get("my_custom_format")
assert parser is not None
assert parser.DOC_TYPE == "invoice"
```

---

## 4. Interface ParserBase

Todo parser debe heredar de `ParserBase`:

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any
from ..domain.canonical_schema import CanonicalDocument, CanonicalItem

class ParserBase(ABC):
    """Interface base para todos los parsers."""

    # Metadata requerida (class attributes)
    PARSER_ID: str
    DOC_TYPE: str
    SUPPORTED_EXTENSIONS: List[str]

    @abstractmethod
    async def parse(self, file_path: str, **kwargs) -> CanonicalDocument:
        """Parsear archivo → CanonicalDocument."""
        pass

    @abstractmethod
    def validate(self, item: CanonicalItem) -> bool:
        """Validar item parseado."""
        pass

    def is_compatible(self, filename: str) -> bool:
        """Chequear si parser puede manejar el archivo."""
        ext = Path(filename).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS
```

---

## 5. Estructura de CanonicalDocument

El parser debe retornar datos en este formato:

```python
CanonicalDocument(
    doc_type="invoice",           # invoice|expense|product|bank_tx
    parser_id="csv_invoices",     # ID del parser
    source_file="facturas.csv",   # Nombre original
    items=[                         # Items parseados
        CanonicalItem(
            item_type="invoice",
            fields={
                "invoice_number": "INV-001",
                "date": "2025-01-15",
                "total": 1250.00,
                "currency": "USD",
                "vendor_name": "Supplier A",
                "tax": 150.00
            },
            validation_status="pending",
            line_number=1
        ),
        # ... más items
    ],
    metadata={
        "sheet_name": "Sheet1",
        "encoding": "utf-8",
        "total_rows": 100
    }
)
```

---

## 6. Parsers Existentes

### csv_invoices
```
Parser ID: csv_invoices
Doc Type: invoice
Extensiones: .csv
Campos esperados: invoice_number, date, vendor, total, tax
```

### csv_bank
```
Parser ID: csv_bank
Doc Type: bank_tx
Extensiones: .csv
Campos esperados: date, amount, direction, account, iban
```

### xml_invoice
```
Parser ID: xml_invoice
Doc Type: invoice
Extensiones: .xml
Soporta: UBL, CFDI, FACTURA-E
```

### xml_camt053_bank
```
Parser ID: xml_camt053_bank
Doc Type: bank_tx
Extensiones: .xml
Estándar: ISO 20022 CAMT.053
```

### products_excel
```
Parser ID: products_excel
Doc Type: product
Extensiones: .xlsx, .xls
Campos esperados: name, sku, price, quantity, category
```

### xlsx_expenses
```
Parser ID: xlsx_expenses
Doc Type: expense
Extensiones: .xlsx, .xls
Campos esperados: date, vendor, amount, category, description
```

### pdf_qr
```
Parser ID: pdf_qr
Doc Type: invoice
Extensiones: .pdf
Extrae: códigos QR + OCR básico
```

---

## 7. Ciclo Completo: Parser → Canonical → Handler

```
1. Usuario sube archivo.csv
                ↓
2. classify_file() → detecta "csv_invoices"
                ↓
3. get parser = registry.get("csv_invoices")
                ↓
4. parser.parse(file_path)
   → CanonicalDocument con items
                ↓
5. validate_canonical(doc)
   → Chequea tipos, campos, formatos
                ↓
6. get_country_validator() → validación por país
   → ECValidator, ESValidator, etc.
                ↓
7. handlers_router.dispatch(doc)
   → expense_handler / product_handler / bank_handler
                ↓
8. Persistir en DB: products, invoices, expenses, etc.
```

---

## 8. Testing

### Test unitario simple

```python
# tests/modules/imports/parsers/test_my_custom_parser.py

import pytest
from pathlib import Path
from app.modules.imports.parsers.my_custom_parser import MyCustomParser
from app.modules.imports.domain.canonical_schema import CanonicalDocument

@pytest.fixture
def parser():
    return MyCustomParser()

@pytest.fixture
def sample_file(tmp_path):
    """Crear archivo de prueba."""
    test_file = tmp_path / "test.custom"
    test_file.write_text("...")
    return str(test_file)

@pytest.mark.asyncio
async def test_parse(parser, sample_file):
    """Parsear archivo correctamente."""
    doc = await parser.parse(sample_file)

    assert isinstance(doc, CanonicalDocument)
    assert doc.doc_type == "invoice"
    assert len(doc.items) > 0

@pytest.mark.asyncio
async def test_validate_items(parser, sample_file):
    """Validar items parseados."""
    doc = await parser.parse(sample_file)

    for item in doc.items:
        assert parser.validate(item)

def test_is_compatible(parser):
    """Chequear compatibilidad con extensiones."""
    assert parser.is_compatible("test.custom")
    assert parser.is_compatible("test.txt")
    assert not parser.is_compatible("test.csv")
```

---

## 9. Ejemplo Completo: Parser JSON

```python
# app/modules/imports/parsers/json_invoices.py

import json
from typing import List
from .base import ParserBase
from ..domain.canonical_schema import CanonicalDocument, CanonicalItem

class JSONInvoicesParser(ParserBase):
    """Parser para facturas en JSON."""

    PARSER_ID = "json_invoices"
    DOC_TYPE = "invoice"
    SUPPORTED_EXTENSIONS = [".json"]

    async def parse(self, file_path: str, **kwargs) -> CanonicalDocument:
        """Parsear JSON → CanonicalDocument."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        items = []
        invoices = data if isinstance(data, list) else [data]

        for i, invoice in enumerate(invoices, 1):
            item = CanonicalItem(
                item_type="invoice",
                fields={
                    "invoice_number": invoice.get("number"),
                    "date": invoice.get("date"),
                    "total": invoice.get("total"),
                    "vendor_name": invoice.get("vendor"),
                    "tax": invoice.get("tax")
                },
                validation_status="pending",
                line_number=i
            )
            items.append(item)

        return CanonicalDocument(
            doc_type=self.DOC_TYPE,
            parser_id=self.PARSER_ID,
            source_file=Path(file_path).name,
            items=items,
            metadata={"format": "json", "total_items": len(items)}
        )

    def validate(self, item: CanonicalItem) -> bool:
        """Validar campos requeridos."""
        required = ["invoice_number", "date", "total"]
        return all(item.fields.get(f) for f in required)
```

**Registrar:**
```python
# En app/modules/imports/parsers/__init__.py

from .json_invoices import JSONInvoicesParser

registry.register(
    parser_id="json_invoices",
    parser_class=JSONInvoicesParser,
    metadata=ParserMetadata(
        id="json_invoices",
        doc_type="invoice",
        handler="expense_handler",
        extensions=[".json"],
        description="Parser para facturas en JSON",
        version="1.0.0"
    )
)
```

---

## 10. Mejores Prácticas

1. **Siempre heredar de `ParserBase`**
2. **Validar datos de entrada** (encoding, estructura)
3. **Retornar `CanonicalDocument` válido**
4. **Implementar logging** para debugging
5. **Manejar excepciones gracefully**
6. **Registrar en `__init__.py`** después de crear
7. **Crear tests unitarios**
8. **Documentar campos esperados**

---

## 11. Troubleshooting

| Problema | Solución |
|----------|----------|
| Parser no se carga | Verificar que está registrado en `__init__.py` |
| Import error | Chequear que clase hereda de `ParserBase` |
| Validación falla | Revisar que `validate()` chequea campos correctos |
| Encoding issues | Especificar encoding explícitamente |
| Performance lento | Usar async/await, evitar I/O sincrónico |

---

## Resumen

```
1. Crea archivo: parsers/my_format.py
2. Hereda de ParserBase
3. Implementa: parse(), validate()
4. Registra en: parsers/__init__.py
5. Añade tests
6. Listo para usar
```

**Tiempo estimado:** 30-60 minutos por parser nuevo
