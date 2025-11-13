"""
Benchmark validadores: medir latencia de reglas de validación.
Target: < 10ms por item.
"""

import time
import json
import statistics
from typing import List, Dict, Any
from pathlib import Path


def benchmark_invoice_validation(iterations: int = 100) -> Dict[str, Any]:
    """
    Benchmark validación de factura (reglas EC).
    """
    from app.modules.imports.validators import validate_invoices

    invoice = {
        "proveedor": {
            "tax_id": "1790016919001",
            "nombre": "Test S.A.",
        },
        "cliente": {
            "tax_id": "0992345678001",
            "nombre": "Cliente",
        },
        "totales": {
            "subtotal": 100.0,
            "iva": 12.0,
            "total": 112.0,
        },
        "lineas": [
            {
                "descripcion": "Item",
                "cantidad": 1,
                "precio_unitario": 100.0,
                "subtotal": 100.0,
            }
        ],
        "fecha_emision": "2025-01-15",
    }

    latencies: List[float] = []

    for _ in range(iterations):
        start = time.perf_counter()
        errors = validate_invoices(invoice, country="EC")  # noqa: F841
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

    p95 = sorted(latencies)[int(0.95 * len(latencies))]

    return {
        "test": "invoice_validation",
        "iterations": iterations,
        "mean_ms": statistics.mean(latencies) * 1000,
        "p95_ms": p95 * 1000,
        "target_p95_ms": 10,
        "passed": p95 < 0.01,
    }


def benchmark_bank_validation(iterations: int = 100) -> Dict[str, Any]:
    """
    Benchmark validación de movimientos bancarios.
    """
    from app.modules.imports.validators import validate_bank

    movement = {
        "cuenta_iban": "EC1234567890123456789012",
        "fecha_valor": "2025-01-15",
        "concepto": "Transferencia",
        "importe": 500.0,
        "saldo": 1500.0,
    }

    latencies: List[float] = []

    for _ in range(iterations):
        start = time.perf_counter()
        errors = validate_bank(movement)  # noqa: F841
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

    p95 = sorted(latencies)[int(0.95 * len(latencies))]

    return {
        "test": "bank_validation",
        "iterations": iterations,
        "mean_ms": statistics.mean(latencies) * 1000,
        "p95_ms": p95 * 1000,
        "target_p95_ms": 10,
        "passed": p95 < 0.01,
    }


def benchmark_batch_validation(batch_size: int = 100) -> Dict[str, Any]:
    """
    Benchmark validación de batch completo.
    Target: < 1s para 100 items.
    """
    from app.modules.imports.validators import validate_invoices

    invoices = []
    for i in range(batch_size):
        invoices.append(
            {
                "proveedor": {"tax_id": "1790016919001", "nombre": f"Proveedor {i}"},
                "totales": {"subtotal": 100.0, "iva": 12.0, "total": 112.0},
            }
        )

    start = time.perf_counter()
    for inv in invoices:
        validate_invoices(inv, country="EC")
    elapsed = time.perf_counter() - start

    return {
        "test": "batch_validation",
        "batch_size": batch_size,
        "total_ms": elapsed * 1000,
        "per_item_ms": (elapsed / batch_size) * 1000,
        "target_total_ms": 1000,
        "passed": elapsed < 1.0,
    }


def run_all_benchmarks() -> Dict[str, Any]:
    """Ejecuta todos los benchmarks de validación."""
    import datetime

    print("🔥 Running validation benchmarks...\n")

    results = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "benchmarks": [],
    }

    print("1️⃣  Invoice validation...")
    results["benchmarks"].append(benchmark_invoice_validation(iterations=100))

    print("2️⃣  Bank validation...")
    results["benchmarks"].append(benchmark_bank_validation(iterations=100))

    print("3️⃣  Batch validation (100 items)...")
    results["benchmarks"].append(benchmark_batch_validation(batch_size=100))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for bench in results["benchmarks"]:
        status = "✅ PASS" if bench.get("passed", False) else "❌ FAIL"
        test_name = bench["test"]

        if "p95_ms" in bench:
            print(f"{status} {test_name}: P95={bench['p95_ms']:.3f}ms")
        elif "total_ms" in bench:
            print(
                f"{status} {test_name}: Total={bench['total_ms']:.1f}ms ({bench['per_item_ms']:.2f}ms/item)"
            )

    return results


if __name__ == "__main__":
    results = run_all_benchmarks()

    output_path = (
        Path(__file__).parent / f"bench_validation_results_{int(time.time())}.json"
    )
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📊 Results saved to: {output_path}")
