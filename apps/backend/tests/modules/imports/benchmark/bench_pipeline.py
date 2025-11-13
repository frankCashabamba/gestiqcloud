"""
Benchmark end-to-end pipeline: ingest → extract → validate → promote.
Target: < 30s para batch de 10 items (sin OCR real).
"""

import json
import statistics
import time
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


def benchmark_full_pipeline_batch(
    db: Session,
    tenant_id: str,
    batch_size: int = 10,
) -> dict[str, Any]:
    """
    Benchmark pipeline completo con batch sintético.
    """
    from app.modules.imports.application.use_cases import (
        create_batch,
        ingest_file,
        promote_batch,
        validate_item_sync,
    )

    # 1. Crear batch
    start_total = time.perf_counter()

    batch = create_batch(
        db=db,
        tenant_id=tenant_id,
        source_type="invoices",
        description=f"Benchmark batch {batch_size} items",
    )

    create_time = time.perf_counter() - start_total

    # 2. Ingestar items
    start_ingest = time.perf_counter()
    items = []
    for i in range(batch_size):
        item = ingest_file(
            db=db,
            tenant_id=tenant_id,
            batch_id=batch.id,
            file_key=f"bench/{i}.pdf",
            filename=f"bench_{i}.pdf",
            file_size=1024,
            file_sha256=f"bench_sha_{i}",
        )
        items.append(item)
    ingest_time = time.perf_counter() - start_ingest

    # 3. Extract (mock, sin OCR)
    start_extract = time.perf_counter()
    for item in items:
        # Mock normalized
        item.normalized = {
            "proveedor": {"tax_id": "1790016919001", "nombre": "Test"},
            "totales": {"subtotal": 100.0, "iva": 12.0, "total": 112.0},
        }
        item.status = "extracted"
        db.add(item)
    db.commit()
    extract_time = time.perf_counter() - start_extract

    # 4. Validate
    start_validate = time.perf_counter()
    for item in items:
        validate_item_sync(db, tenant_id, str(item.id))
    validate_time = time.perf_counter() - start_validate

    # 5. Promote
    start_promote = time.perf_counter()
    promote_batch(db, tenant_id, batch.id)
    promote_time = time.perf_counter() - start_promote

    total_time = time.perf_counter() - start_total

    return {
        "test": "full_pipeline_batch",
        "batch_size": batch_size,
        "create_ms": create_time * 1000,
        "ingest_ms": ingest_time * 1000,
        "extract_ms": extract_time * 1000,
        "validate_ms": validate_time * 1000,
        "promote_ms": promote_time * 1000,
        "total_ms": total_time * 1000,
        "per_item_ms": (total_time / batch_size) * 1000,
        "target_total_ms": 30000,
        "passed": total_time < 30.0,
    }


def benchmark_promotion_throughput(iterations: int = 50) -> dict[str, Any]:
    """
    Benchmark throughput de promoción (sin DB real, solo lógica).
    """
    from app.modules.imports.domain.handlers import InvoiceHandler

    normalized = {
        "proveedor": {"tax_id": "1790016919001", "nombre": "Test"},
        "totales": {"subtotal": 100.0, "iva": 12.0, "total": 112.0},
        "fecha_emision": "2025-01-15",
    }

    latencies = []

    for _ in range(iterations):
        start = time.perf_counter()
        result = InvoiceHandler.promote(normalized, promoted_id=None)  # noqa: F841
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

    return {
        "test": "promotion_throughput",
        "iterations": iterations,
        "mean_ms": statistics.mean(latencies) * 1000,
        "p95_ms": sorted(latencies)[int(0.95 * len(latencies))] * 1000,
        "throughput_per_sec": 1.0 / statistics.mean(latencies),
    }


def run_all_benchmarks() -> dict[str, Any]:
    """Ejecuta todos los benchmarks de pipeline."""
    import datetime

    print("🔥 Running pipeline benchmarks...\n")

    results = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "benchmarks": [],
    }

    # Setup DB de prueba
    db = SessionLocal()
    tenant_id = "test-tenant-bench"
    tenant_id = 999

    try:
        db.execute(f"SET LOCAL app.tenant_id = '{tenant_id}'")

        print("1️⃣  Full pipeline (10 items)...")
        bench1 = benchmark_full_pipeline_batch(db, tenant_id, tenant_id, batch_size=10)
        results["benchmarks"].append(bench1)

        print("2️⃣  Promotion throughput...")
        bench2 = benchmark_promotion_throughput(iterations=50)
        results["benchmarks"].append(bench2)

    finally:
        db.close()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for bench in results["benchmarks"]:
        status = "✅ PASS" if bench.get("passed", False) else "⚠️ "
        test_name = bench["test"]

        if "total_ms" in bench:
            print(
                f"{status} {test_name}: {bench['total_ms']:.1f}ms total ({bench['per_item_ms']:.1f}ms/item)"
            )
        elif "throughput_per_sec" in bench:
            print(f"{status} {test_name}: {bench['throughput_per_sec']:.0f} items/sec")

    return results


if __name__ == "__main__":
    results = run_all_benchmarks()

    output_path = Path(__file__).parent / f"bench_pipeline_results_{int(time.time())}.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📊 Results saved to: {output_path}")
