#!/usr/bin/env python3
"""
Setup script para generar datos de prueba para benchmarks de ElectricSQL.

Genera un dataset de ~100MB con:
- 10,000 productos
- 5,000 clientes
- 20,000 recibos POS

Uso:
    python setup.py          # Genera datos
    python setup.py --clean  # Limpia y regenera
"""

import argparse
import json
import os
import random
import string
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "test_data"
RESULTS_DIR = Path(__file__).parent / "results"

NUM_PRODUCTS = 10_000
NUM_CLIENTS = 5_000
NUM_RECEIPTS = 20_000

TENANT_ID = os.getenv("TEST_TENANT_ID", "bench_tenant_001")


def random_string(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def random_date(start_days_ago: int = 365) -> str:
    days_ago = random.randint(0, start_days_ago)
    date = datetime.now() - timedelta(days=days_ago)
    return date.isoformat()


def generate_products() -> list[dict]:
    """Genera 10K productos (~30MB)."""
    print(f"Generando {NUM_PRODUCTS:,} productos...")
    products = []
    categories = ["Electronics", "Clothing", "Food", "Home", "Sports", "Books", "Toys"]

    for i in range(NUM_PRODUCTS):
        products.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": TENANT_ID,
                "sku": f"SKU-{i:06d}",
                "name": f"Product {random_string(20)}",
                "description": f"Description for product {i}. " * 5,
                "category": random.choice(categories),
                "price": round(random.uniform(1.0, 9999.99), 2),
                "stock": random.randint(0, 10000),
                "barcode": f"{random.randint(1000000000000, 9999999999999)}",
                "created_at": random_date(),
                "updated_at": random_date(30),
                "is_active": random.random() > 0.1,
            }
        )

        if (i + 1) % 2000 == 0:
            print(f"  {i + 1:,}/{NUM_PRODUCTS:,} productos generados")

    return products


def generate_clients() -> list[dict]:
    """Genera 5K clientes (~15MB)."""
    print(f"Generando {NUM_CLIENTS:,} clientes...")
    clients = []

    for i in range(NUM_CLIENTS):
        clients.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": TENANT_ID,
                "code": f"CLI-{i:05d}",
                "name": f"Client {random_string(15)} {random_string(15)}",
                "email": f"client{i}@example.com",
                "phone": f"+1{random.randint(1000000000, 9999999999)}",
                "address": f"{random.randint(1, 9999)} {random_string(10)} Street",
                "city": random.choice(
                    ["Lima", "Arequipa", "Cusco", "Trujillo", "Piura"]
                ),
                "tax_id": f"{random.randint(10000000000, 99999999999)}",
                "credit_limit": round(random.uniform(0, 50000), 2),
                "created_at": random_date(),
                "updated_at": random_date(30),
                "is_active": random.random() > 0.05,
            }
        )

        if (i + 1) % 1000 == 0:
            print(f"  {i + 1:,}/{NUM_CLIENTS:,} clientes generados")

    return clients


def generate_receipts(products: list[dict], clients: list[dict]) -> list[dict]:
    """Genera 20K recibos POS (~55MB)."""
    print(f"Generando {NUM_RECEIPTS:,} recibos...")
    receipts = []
    payment_methods = ["cash", "card", "transfer", "credit"]

    for i in range(NUM_RECEIPTS):
        num_items = random.randint(1, 10)
        items = []
        subtotal = 0.0

        for _ in range(num_items):
            product = random.choice(products)
            qty = random.randint(1, 5)
            price = product["price"]
            items.append(
                {
                    "product_id": product["id"],
                    "sku": product["sku"],
                    "name": product["name"],
                    "quantity": qty,
                    "unit_price": price,
                    "total": round(qty * price, 2),
                }
            )
            subtotal += qty * price

        tax = round(subtotal * 0.18, 2)
        total = round(subtotal + tax, 2)

        receipts.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": TENANT_ID,
                "receipt_number": f"REC-{i:06d}",
                "client_id": random.choice(clients)["id"]
                if random.random() > 0.3
                else None,
                "items": items,
                "subtotal": round(subtotal, 2),
                "tax": tax,
                "total": total,
                "payment_method": random.choice(payment_methods),
                "status": random.choice(
                    ["completed", "completed", "completed", "voided"]
                ),
                "created_at": random_date(),
                "synced_at": None,
                "offline_created": random.random() > 0.7,
            }
        )

        if (i + 1) % 5000 == 0:
            print(f"  {i + 1:,}/{NUM_RECEIPTS:,} recibos generados")

    return receipts


def save_data(data: dict, filename: str) -> int:
    """Guarda datos en JSON y retorna tamaño en bytes."""
    filepath = DATA_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f)
    size = filepath.stat().st_size
    print(f"  Guardado: {filename} ({size / 1024 / 1024:.2f} MB)")
    return size


def clean_data():
    """Elimina datos de prueba existentes."""
    if DATA_DIR.exists():
        for f in DATA_DIR.glob("*.json"):
            f.unlink()
        print("Datos anteriores eliminados")


def main():
    parser = argparse.ArgumentParser(
        description="Genera datos de prueba para benchmarks"
    )
    parser.add_argument("--clean", action="store_true", help="Limpiar datos existentes")
    args = parser.parse_args()

    DATA_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)

    if args.clean:
        clean_data()

    print(f"\n{'=' * 60}")
    print("GENERADOR DE DATOS DE PRUEBA - ElectricSQL Benchmarks")
    print(f"{'=' * 60}")
    print(f"Tenant ID: {TENANT_ID}")
    print(f"Destino: {DATA_DIR}")
    print()

    products = generate_products()
    clients = generate_clients()
    receipts = generate_receipts(products, clients)

    print("\nGuardando datos...")
    total_size = 0
    total_size += save_data(products, "products.json")
    total_size += save_data(clients, "clients.json")
    total_size += save_data(receipts, "receipts.json")

    metadata = {
        "generated_at": datetime.now().isoformat(),
        "tenant_id": TENANT_ID,
        "counts": {
            "products": len(products),
            "clients": len(clients),
            "receipts": len(receipts),
        },
        "total_size_mb": round(total_size / 1024 / 1024, 2),
    }
    save_data(metadata, "metadata.json")

    print(f"\n{'=' * 60}")
    print("RESUMEN")
    print(f"{'=' * 60}")
    print(f"Productos: {len(products):,}")
    print(f"Clientes: {len(clients):,}")
    print(f"Recibos: {len(receipts):,}")
    print(f"Tamaño total: {total_size / 1024 / 1024:.2f} MB")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
