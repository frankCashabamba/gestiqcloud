#!/usr/bin/env python3
"""
Benchmark de shapes (filtros) ElectricSQL.

Mide latencia de shapes con diferentes tamaños de datos:
- Filtro por tenant_id
- Filtro por fecha
- Filtro por categoría
- Filtros combinados

Objetivo P95: < 200ms
"""

import asyncio
import json
import os
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "test_data"
RESULTS_DIR = Path(__file__).parent / "results"

ELECTRIC_URL = os.getenv("ELECTRIC_URL", "ws://localhost:5133")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TENANT_ID = os.getenv("TEST_TENANT_ID", "bench_tenant_001")

SHAPE_FILTER_TARGET_MS = 200
NUM_ITERATIONS = 20


@dataclass
class ShapeBenchmarkResult:
    name: str
    filter_type: str
    data_size: int
    target_ms: float
    measurements_ms: list[float] = field(default_factory=list)

    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.measurements_ms) if self.measurements_ms else 0

    @property
    def p95_ms(self) -> float:
        if not self.measurements_ms:
            return 0
        sorted_vals = sorted(self.measurements_ms)
        idx = int(len(sorted_vals) * 0.95)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    @property
    def p99_ms(self) -> float:
        if not self.measurements_ms:
            return 0
        sorted_vals = sorted(self.measurements_ms)
        idx = int(len(sorted_vals) * 0.99)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    @property
    def passed(self) -> bool:
        return self.p95_ms < self.target_ms

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "filter_type": self.filter_type,
            "data_size": self.data_size,
            "target_ms": self.target_ms,
            "mean_ms": round(self.mean_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "passed": self.passed,
            "iterations": len(self.measurements_ms),
        }


def load_test_data() -> dict[str, list[dict]]:
    """Carga datos de prueba generados por setup.py."""
    data = {}
    for table in ["products", "clients", "receipts"]:
        filepath = DATA_DIR / f"{table}.json"
        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                data[table] = json.load(f)
        else:
            data[table] = []
    return data


class MockShapeSubscription:
    """
    Mock para simular shape subscriptions de ElectricSQL.
    En producción real, usar el SDK de ElectricSQL.
    """

    def __init__(self, data: list[dict]):
        self.source_data = data

    async def subscribe(
        self, where_clause: dict, limit: int | None = None
    ) -> tuple[list[dict], float]:
        """Aplica filtro y retorna datos + latencia."""
        start = time.perf_counter()

        filtered = self.source_data.copy()

        for key, value in where_clause.items():
            if isinstance(value, dict):
                if "$gte" in value:
                    filtered = [r for r in filtered if r.get(key, "") >= value["$gte"]]
                if "$lte" in value:
                    filtered = [r for r in filtered if r.get(key, "") <= value["$lte"]]
                if "$in" in value:
                    filtered = [r for r in filtered if r.get(key) in value["$in"]]
            else:
                filtered = [r for r in filtered if r.get(key) == value]

        if limit:
            filtered = filtered[:limit]

        base_latency = len(self.source_data) * 0.000005
        filter_latency = len(filtered) * 0.00001
        jitter = (time.perf_counter() % 0.02) * 0.5
        await asyncio.sleep(base_latency + filter_latency + jitter)

        elapsed_ms = (time.perf_counter() - start) * 1000
        return filtered, elapsed_ms


async def benchmark_tenant_filter(data: dict) -> ShapeBenchmarkResult:
    """Benchmark: filtro por tenant_id."""
    products = data.get("products", [])
    shape = MockShapeSubscription(products)

    result = ShapeBenchmarkResult(
        name="tenant_filter",
        filter_type="tenant_id = ?",
        data_size=len(products),
        target_ms=SHAPE_FILTER_TARGET_MS,
    )

    print("\n[Benchmark] Filtro por Tenant ID")
    print(f"   Dataset: {len(products):,} productos")
    print(f"   Target P95: < {SHAPE_FILTER_TARGET_MS}ms")

    for i in range(NUM_ITERATIONS):
        filtered, elapsed_ms = await shape.subscribe({"tenant_id": TENANT_ID})
        result.measurements_ms.append(elapsed_ms)

        if (i + 1) % 5 == 0:
            status = "PASS" if elapsed_ms < SHAPE_FILTER_TARGET_MS else "FAIL"
            print(
                f"   [{i + 1}/{NUM_ITERATIONS}] {elapsed_ms:.2f}ms ({len(filtered):,} results) [{status}]"
            )

    return result


async def benchmark_date_range_filter(data: dict) -> ShapeBenchmarkResult:
    """Benchmark: filtro por rango de fechas."""
    receipts = data.get("receipts", [])
    shape = MockShapeSubscription(receipts)

    result = ShapeBenchmarkResult(
        name="date_range_filter",
        filter_type="created_at BETWEEN ? AND ?",
        data_size=len(receipts),
        target_ms=SHAPE_FILTER_TARGET_MS,
    )

    print("\n[Benchmark] Filtro por Rango de Fechas")
    print(f"   Dataset: {len(receipts):,} recibos")
    print(f"   Target P95: < {SHAPE_FILTER_TARGET_MS}ms")

    end_date = datetime.now().isoformat()
    start_date = (datetime.now() - timedelta(days=30)).isoformat()

    for i in range(NUM_ITERATIONS):
        filtered, elapsed_ms = await shape.subscribe(
            {"created_at": {"$gte": start_date, "$lte": end_date}}
        )
        result.measurements_ms.append(elapsed_ms)

        if (i + 1) % 5 == 0:
            status = "PASS" if elapsed_ms < SHAPE_FILTER_TARGET_MS else "FAIL"
            print(
                f"   [{i + 1}/{NUM_ITERATIONS}] {elapsed_ms:.2f}ms ({len(filtered):,} results) [{status}]"
            )

    return result


async def benchmark_category_filter(data: dict) -> ShapeBenchmarkResult:
    """Benchmark: filtro por categoría."""
    products = data.get("products", [])
    shape = MockShapeSubscription(products)

    result = ShapeBenchmarkResult(
        name="category_filter",
        filter_type="category IN (?)",
        data_size=len(products),
        target_ms=SHAPE_FILTER_TARGET_MS,
    )

    print("\n[Benchmark] Filtro por Categoria")
    print(f"   Dataset: {len(products):,} productos")
    print(f"   Target P95: < {SHAPE_FILTER_TARGET_MS}ms")

    categories = ["Electronics", "Clothing", "Food"]

    for i in range(NUM_ITERATIONS):
        filtered, elapsed_ms = await shape.subscribe({"category": {"$in": categories}})
        result.measurements_ms.append(elapsed_ms)

        if (i + 1) % 5 == 0:
            status = "PASS" if elapsed_ms < SHAPE_FILTER_TARGET_MS else "FAIL"
            print(
                f"   [{i + 1}/{NUM_ITERATIONS}] {elapsed_ms:.2f}ms ({len(filtered):,} results) [{status}]"
            )

    return result


async def benchmark_combined_filter(data: dict) -> ShapeBenchmarkResult:
    """Benchmark: filtros combinados."""
    products = data.get("products", [])
    shape = MockShapeSubscription(products)

    result = ShapeBenchmarkResult(
        name="combined_filter",
        filter_type="tenant_id = ? AND category = ? AND is_active = ?",
        data_size=len(products),
        target_ms=SHAPE_FILTER_TARGET_MS,
    )

    print("\n[Benchmark] Filtros Combinados")
    print(f"   Dataset: {len(products):,} productos")
    print(f"   Target P95: < {SHAPE_FILTER_TARGET_MS}ms")

    for i in range(NUM_ITERATIONS):
        filtered, elapsed_ms = await shape.subscribe(
            {
                "tenant_id": TENANT_ID,
                "category": "Electronics",
                "is_active": True,
            }
        )
        result.measurements_ms.append(elapsed_ms)

        if (i + 1) % 5 == 0:
            status = "PASS" if elapsed_ms < SHAPE_FILTER_TARGET_MS else "FAIL"
            print(
                f"   [{i + 1}/{NUM_ITERATIONS}] {elapsed_ms:.2f}ms ({len(filtered):,} results) [{status}]"
            )

    return result


async def benchmark_large_result_set(data: dict) -> ShapeBenchmarkResult:
    """Benchmark: shape que retorna muchos registros."""
    receipts = data.get("receipts", [])
    shape = MockShapeSubscription(receipts)

    result = ShapeBenchmarkResult(
        name="large_result_set",
        filter_type="status = 'completed' (large result)",
        data_size=len(receipts),
        target_ms=SHAPE_FILTER_TARGET_MS * 2,
    )

    print("\n[Benchmark] Result Set Grande")
    print(f"   Dataset: {len(receipts):,} recibos")
    print(f"   Target P95: < {SHAPE_FILTER_TARGET_MS * 2}ms (2x normal)")

    for i in range(NUM_ITERATIONS):
        filtered, elapsed_ms = await shape.subscribe({"status": "completed"})
        result.measurements_ms.append(elapsed_ms)

        if (i + 1) % 5 == 0:
            status = "PASS" if elapsed_ms < SHAPE_FILTER_TARGET_MS * 2 else "FAIL"
            print(
                f"   [{i + 1}/{NUM_ITERATIONS}] {elapsed_ms:.2f}ms ({len(filtered):,} results) [{status}]"
            )

    return result


def print_summary(results: list[ShapeBenchmarkResult]) -> None:
    """Imprime resumen de resultados."""
    print(f"\n{'=' * 60}")
    print("RESUMEN DE BENCHMARKS - ElectricSQL Shapes")
    print(f"{'=' * 60}")

    all_passed = True
    for result in results:
        status = "[PASS]" if result.passed else "[FAIL]"
        all_passed = all_passed and result.passed
        print(f"\n{result.name}:")
        print(f"   Filter: {result.filter_type}")
        print(f"   Mean: {result.mean_ms:.2f}ms")
        print(f"   P95:  {result.p95_ms:.2f}ms (target: {result.target_ms}ms) {status}")

    print(f"\n{'=' * 60}")
    overall = (
        "[PASS] ALL BENCHMARKS PASSED"
        if all_passed
        else "[FAIL] SOME BENCHMARKS FAILED"
    )
    print(overall)
    print(f"{'=' * 60}")


def save_results(results: list[ShapeBenchmarkResult]) -> None:
    """Guarda resultados en JSON."""
    RESULTS_DIR.mkdir(exist_ok=True)

    output = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "electric_url": ELECTRIC_URL,
            "api_base_url": API_BASE_URL,
            "tenant_id": TENANT_ID,
            "iterations": NUM_ITERATIONS,
            "target_ms": SHAPE_FILTER_TARGET_MS,
        },
        "benchmarks": [r.to_dict() for r in results],
        "all_passed": all(r.passed for r in results),
    }

    filepath = RESULTS_DIR / "shapes_benchmark.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nResultados guardados en: {filepath}")


async def main() -> int:
    print(f"\n{'=' * 60}")
    print("BENCHMARKS DE SHAPES - ElectricSQL")
    print(f"{'=' * 60}")
    print(f"Electric URL: {ELECTRIC_URL}")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Tenant ID: {TENANT_ID}")
    print(f"Target P95: < {SHAPE_FILTER_TARGET_MS}ms")

    data = load_test_data()
    if not any(data.values()):
        print("\n❌ No hay datos de prueba. Ejecuta: python setup.py")
        return 1

    print("\nDataset cargado:")
    for table, records in data.items():
        print(f"  {table}: {len(records):,} registros")

    results = []

    results.append(await benchmark_tenant_filter(data))
    results.append(await benchmark_date_range_filter(data))
    results.append(await benchmark_category_filter(data))
    results.append(await benchmark_combined_filter(data))
    results.append(await benchmark_large_result_set(data))

    print_summary(results)
    save_results(results)

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
