#!/usr/bin/env python3
"""
Script para regenerar golden outputs cuando los extractores cambian.
Uso: python update_golden.py
"""

import json
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden_outputs"
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "documents"


def update_invoice_ec():
    """Regenera golden para factura EC."""
    from app.modules.imports.extractores.invoice_extractor import extract_invoice

    pdf_path = FIXTURES_DIR / "factura_ec_sample.pdf"
    with open(pdf_path, "rb") as f:
        extracted = extract_invoice(f.read(), country="EC")

    normalized = {
        "proveedor": extracted.get("proveedor", {}),
        "cliente": extracted.get("cliente", {}),
        "totales": extracted.get("totales", {}),
        "fecha_emision": extracted.get("fecha_emision"),
        "numero_factura": extracted.get("numero_factura"),
    }

    output_path = GOLDEN_DIR / "factura_ec_sample.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated {output_path}")


def update_bank_csv():
    """Regenera golden para CSV bancario."""
    from app.modules.imports.extractores.bank_extractor import extract_bank_csv

    csv_path = FIXTURES_DIR / "banco_movimientos.csv"
    with open(csv_path, encoding="utf-8") as f:
        extracted = extract_bank_csv(f.read())

    output_path = GOLDEN_DIR / "banco_movimientos.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted, f, indent=2, ensure_ascii=False)

    print(f"✅ Updated {output_path}")


def main():
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    print("🔄 Regenerando golden outputs...")

    try:
        update_invoice_ec()
        update_bank_csv()
        print("\n✅ Todos los golden outputs actualizados.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
