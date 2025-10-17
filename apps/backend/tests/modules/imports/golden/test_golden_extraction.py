"""
Golden tests: verifica que extractores produzcan output consistente.
Útil para detectar regresiones en lógica de extracción.
"""
import json
from pathlib import Path
from typing import Dict, Any

import pytest


GOLDEN_DIR = Path(__file__).parent / "golden_outputs"


def load_golden(filename: str) -> Dict[str, Any]:
    """Carga output esperado desde golden_outputs/."""
    path = GOLDEN_DIR / filename
    if not path.exists():
        pytest.skip(f"Golden output no existe: {filename}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_golden(filename: str, data: Dict[str, Any]):
    """Guarda output como golden (para regenerar)."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    path = GOLDEN_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@pytest.mark.golden
def test_golden_invoice_ec_extraction():
    """
    Verifica que extractor de facturas EC produzca output esperado.
    """
    from app.modules.imports.extractores.invoice_extractor import extract_invoice
    
    # PDF de muestra
    pdf_path = Path(__file__).parent.parent / "fixtures" / "documents" / "factura_ec_sample.pdf"
    
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()
    
    # Extraer
    extracted = extract_invoice(pdf_content, country="EC")
    
    # Normalizar campos que pueden variar (timestamps, IDs)
    normalized = {
        "proveedor": extracted.get("proveedor", {}),
        "cliente": extracted.get("cliente", {}),
        "totales": extracted.get("totales", {}),
        "fecha_emision": extracted.get("fecha_emision"),
        "numero_factura": extracted.get("numero_factura"),
    }
    
    # Comparar con golden
    golden = load_golden("factura_ec_sample.json")
    
    assert normalized == golden, (
        f"Output difiere del golden.\n"
        f"Expected: {json.dumps(golden, indent=2)}\n"
        f"Got: {json.dumps(normalized, indent=2)}"
    )


@pytest.mark.golden
def test_golden_bank_csv_extraction():
    """
    Verifica que parser de CSV bancario produzca output esperado.
    """
    from app.modules.imports.extractores.bank_extractor import extract_bank_csv
    
    csv_path = Path(__file__).parent.parent / "fixtures" / "documents" / "banco_movimientos.csv"
    
    with open(csv_path, "r", encoding="utf-8") as f:
        csv_content = f.read()
    
    # Extraer
    extracted = extract_bank_csv(csv_content)
    
    # Comparar con golden
    golden = load_golden("banco_movimientos.json")
    
    assert len(extracted) == len(golden)
    
    for idx, (item, golden_item) in enumerate(zip(extracted, golden)):
        assert item == golden_item, (
            f"Item {idx} difiere del golden.\n"
            f"Expected: {json.dumps(golden_item, indent=2)}\n"
            f"Got: {json.dumps(item, indent=2)}"
        )


@pytest.mark.golden
def test_golden_validation_errors():
    """
    Verifica que validador produzca errores consistentes.
    """
    from app.modules.imports.validators import validate_invoices
    
    # Factura con errores conocidos
    invalid_invoice = {
        "proveedor": {
            "tax_id": "INVALID_RUC",  # RUC inválido
            "nombre": "Test",
        },
        "totales": {
            "subtotal": 100.0,
            "iva": 12.0,
            "total": 111.0,  # Total no cuadra (debería ser 112)
        },
    }
    
    errors = validate_invoices(invalid_invoice, country="EC")
    
    # Normalizar (quitar mensajes dinámicos si los hay)
    error_codes = [e["code"] for e in errors]
    
    golden_codes = load_golden("validation_errors_invoice.json")
    
    assert sorted(error_codes) == sorted(golden_codes)


def test_update_golden_outputs():
    """
    Test manual para regenerar golden outputs.
    Ejecutar con: pytest -k test_update_golden_outputs --update-golden
    """
    import sys
    if "--update-golden" not in sys.argv:
        pytest.skip("Usa --update-golden para regenerar")
    
    # Regenerar todos los golden outputs
    from app.modules.imports.extractores.invoice_extractor import extract_invoice
    from app.modules.imports.extractores.bank_extractor import extract_bank_csv
    
    # Factura EC
    pdf_path = Path(__file__).parent.parent / "fixtures" / "documents" / "factura_ec_sample.pdf"
    with open(pdf_path, "rb") as f:
        extracted = extract_invoice(f.read(), country="EC")
    save_golden("factura_ec_sample.json", {
        "proveedor": extracted.get("proveedor", {}),
        "cliente": extracted.get("cliente", {}),
        "totales": extracted.get("totales", {}),
        "fecha_emision": extracted.get("fecha_emision"),
        "numero_factura": extracted.get("numero_factura"),
    })
    
    # Banco CSV
    csv_path = Path(__file__).parent.parent / "fixtures" / "documents" / "banco_movimientos.csv"
    with open(csv_path, "r") as f:
        extracted_bank = extract_bank_csv(f.read())
    save_golden("banco_movimientos.json", extracted_bank)
    
    print("Golden outputs actualizados.")
