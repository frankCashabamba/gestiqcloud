"""Script to generate sample fixture files for testing."""

import csv
import os
from pathlib import Path

import openpyxl


def generate_sample_products_xlsx(output_path: Path) -> None:
    """Generate sample products Excel file."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Products"

    headers = ["nombre", "precio", "stock", "categoria", "sku", "descripcion"]
    ws.append(headers)

    products = [
        ["Laptop HP", 999.99, 10, "Electrónica", "LAP-001", "Laptop 15 pulgadas"],
        ["Mouse Logitech", 29.99, 50, "Accesorios", "MOU-001", "Mouse inalámbrico"],
        ["Teclado Mecánico", 79.99, 25, "Accesorios", "TEC-001", "Teclado RGB"],
        ["Monitor Samsung", 299.99, 15, "Monitores", "MON-001", "Monitor 24 pulgadas"],
        ["Auriculares Sony", 149.99, 30, "Audio", "AUR-001", "Auriculares Bluetooth"],
    ]
    for product in products:
        ws.append(product)

    wb.save(output_path)
    print(f"Generated: {output_path}")


def generate_sample_bank_csv(output_path: Path) -> None:
    """Generate sample bank CSV file."""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["fecha", "concepto", "importe", "saldo", "referencia"])
        writer.writerow(
            ["2024-01-15", "Transferencia recibida", 1500.00, 5000.00, "TRF-001"]
        )
        writer.writerow(["2024-01-16", "Pago servicios", -200.00, 4800.00, "PAG-001"])
        writer.writerow(["2024-01-17", "Depósito", 500.00, 5300.00, "DEP-001"])
        writer.writerow(
            ["2024-01-18", "Retiro cajero", -100.00, 5200.00, "RET-001"]
        )
    print(f"Generated: {output_path}")


def generate_sample_invoice_pdf_text() -> str:
    """Generate sample invoice text (for mock PDF)."""
    return """
    FACTURA N° 001-0012345
    
    RUC: 12345678901
    Fecha de emisión: 15/01/2024
    
    Cliente: Empresa ABC S.A.
    RUC Cliente: 98765432109
    
    Detalle:
    - Producto A                    $100.00
    - Producto B                    $150.00
    
    Subtotal:                       $250.00
    IVA (18%):                       $45.00
    Total:                          $295.00
    
    Gracias por su compra
    """


def generate_sample_receipt_text() -> str:
    """Generate sample receipt text (for mock image OCR)."""
    return """
    RECIBO DE VENTA
    
    Tienda: Mi Negocio
    Ticket #12345
    Fecha: 15/01/2024 14:30
    
    Producto 1              $10.00
    Producto 2              $15.00
    Producto 3               $5.00
    
    Total:                  $30.00
    Efectivo:               $50.00
    Cambio:                 $20.00
    
    ¡Gracias por su compra!
    """


if __name__ == "__main__":
    fixtures_dir = Path(__file__).parent

    generate_sample_products_xlsx(fixtures_dir / "sample_products.xlsx")
    generate_sample_bank_csv(fixtures_dir / "sample_bank.csv")

    with open(fixtures_dir / "sample_invoice_text.txt", "w", encoding="utf-8") as f:
        f.write(generate_sample_invoice_pdf_text())
    print(f"Generated: {fixtures_dir / 'sample_invoice_text.txt'}")

    with open(fixtures_dir / "sample_receipt_text.txt", "w", encoding="utf-8") as f:
        f.write(generate_sample_receipt_text())
    print(f"Generated: {fixtures_dir / 'sample_receipt_text.txt'}")

    print("\nAll fixtures generated successfully!")
