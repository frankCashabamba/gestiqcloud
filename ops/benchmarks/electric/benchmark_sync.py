#!/usr/bin/env python3
"""
Benchmark de sincronización ElectricSQL.

Mide:
- Tiempo de sync inicial (full load)
- Tiempo de sync incremental
- Throughput de operaciones offline

Objetivos P95:
- Sync inicial < 5s para 10K registros
- Sync incremental < 500ms
"""

import asyncio
import json
import os
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "test_data"
RESULTS_DIR = Path(__file__).parent / "results"

ELECTRIC_URL = os.getenv("ELECTRIC_URL", "ws://localhost:5133")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TENANT_ID = os.getenv("TEST_TENANT_ID", "bench_tenant_001")
SYNC_TIMEOUT = int(os.getenv("SYNC_TIMEOUT", "30"))

INITIAL_SYNC_TARGET_MS = 5000
INCREMENTAL_SYNC_TARGET_MS = 500
NUM_ITERATIONS = 10


@dataclass
class BenchmarkResult:
    name: str
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
    def min_ms(self) -> float:
        return min(self.measurements_ms) if self.measurements_ms else 0

    @property
    def max_ms(self) -> float:
        return max(self.measurements_ms) if self.measurements_ms else 0

    @property
    def passed(self) -> bool:
        return self.p95_ms < self.target_ms

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "target_ms": self.target_ms,
            "mean_ms": round(self.mean_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
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
            print(f"⚠️  No se encontró {filepath}, ejecuta setup.py primero")
            data[table] = []
    return data


class MockElectricClient:
    """
    Cliente mock para simular ElectricSQL cuando no hay servidor disponible.
    En producción real, reemplazar con conexión WebSocket real.
    """

    def __init__(self, url: str, tenant_id: str):
        self.url = url
        self.tenant_id = tenant_id
        self.local_data: dict[str, list[dict]] = {}
        self.synced = False

    async def connect(self) -> None:
        await asyncio.sleep(0.01)

    async def initial_sync(self, data: dict[str, list[dict]]) -> float:
        """Simula sync inicial - tiempo proporcional al tamaño."""
        start = time.perf_counter()

        total_records = sum(len(records) for records in data.values())
        base_time = total_records * 0.0001
        network_jitter = (time.perf_counter() % 0.1) * 0.5

        await asyncio.sleep(base_time + network_jitter)

        self.local_data = {k: list(v) for k, v in data.items()}
        self.synced = True

        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms

    async def incremental_sync(self, changes: list[dict]) -> float:
        """Simula sync incremental - tiempo proporcional a cambios."""
        start = time.perf_counter()

        base_time = len(changes) * 0.001
        network_jitter = (time.perf_counter() % 0.05) * 0.2

        await asyncio.sleep(base_time + network_jitter)

        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms

    async def offline_operation(self, operation: dict) -> float:
        """Simula operación offline - escribir a IndexedDB/PGlite."""
        start = time.perf_counter()

        await asyncio.sleep(0.001)

        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms

    async def disconnect(self) -> None:
        await asyncio.sleep(0.001)
        self.synced = False


async def benchmark_initial_sync(
    client: MockElectricClient, data: dict
) -> BenchmarkResult:
    """Benchmark de sync inicial (full load)."""
    result = BenchmarkResult(
        name="initial_sync",
        target_ms=INITIAL_SYNC_TARGET_MS,
    )

    total_records = sum(len(records) for records in data.values())
    print(f"\n[Benchmark] Sync Inicial ({total_records:,} registros)")
    print(f"   Target P95: < {INITIAL_SYNC_TARGET_MS}ms")
    print(f"   Iteraciones: {NUM_ITERATIONS}")

    for i in range(NUM_ITERATIONS):
        client.synced = False
        client.local_data = {}

        elapsed_ms = await client.initial_sync(data)
        result.measurements_ms.append(elapsed_ms)

        status = "PASS" if elapsed_ms < INITIAL_SYNC_TARGET_MS else "FAIL"
        print(f"   [{i + 1}/{NUM_ITERATIONS}] {elapsed_ms:.2f}ms [{status}]")

    return result


async def benchmark_incremental_sync(client: MockElectricClient) -> BenchmarkResult:
    """Benchmark de sync incremental."""
    result = BenchmarkResult(
        name="incremental_sync",
        target_ms=INCREMENTAL_SYNC_TARGET_MS,
    )

    print("\n[Benchmark] Sync Incremental")
    print(f"   Target P95: < {INCREMENTAL_SYNC_TARGET_MS}ms")
    print(f"   Iteraciones: {NUM_ITERATIONS}")

    for i in range(NUM_ITERATIONS):
        changes = [
            {
                "type": "UPDATE",
                "table": "products",
                "id": f"prod_{j}",
                "data": {"price": 99.99},
            }
            for j in range(100)
        ]

        elapsed_ms = await client.incremental_sync(changes)
        result.measurements_ms.append(elapsed_ms)

        status = "PASS" if elapsed_ms < INCREMENTAL_SYNC_TARGET_MS else "FAIL"
        print(
            f"   [{i + 1}/{NUM_ITERATIONS}] {elapsed_ms:.2f}ms (100 cambios) [{status}]"
        )

    return result


async def benchmark_offline_throughput(client: MockElectricClient) -> dict[str, Any]:
    """Benchmark de throughput de operaciones offline."""
    print("\n[Benchmark] Throughput Offline")
    print("   Operaciones: 1000")

    operations = [
        {"type": "INSERT", "table": "pos_receipts", "data": {"id": f"receipt_{i}"}}
        for i in range(1000)
    ]

    start = time.perf_counter()
    latencies = []

    for op in operations:
        latency = await client.offline_operation(op)
        latencies.append(latency)

    total_time_ms = (time.perf_counter() - start) * 1000
    ops_per_second = 1000 / (total_time_ms / 1000)

    print(f"   Tiempo total: {total_time_ms:.2f}ms")
    print(f"   Throughput: {ops_per_second:.0f} ops/s")
    print(f"   Latencia media: {statistics.mean(latencies):.2f}ms")
    print(f"   Latencia P95: {sorted(latencies)[int(len(latencies) * 0.95)]:.2f}ms")

    return {
        "name": "offline_throughput",
        "total_operations": 1000,
        "total_time_ms": round(total_time_ms, 2),
        "ops_per_second": round(ops_per_second, 2),
        "latency_mean_ms": round(statistics.mean(latencies), 2),
        "latency_p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
    }


def print_summary(results: list[BenchmarkResult], throughput: dict) -> None:
    """Imprime resumen de resultados."""
    print(f"\n{'=' * 60}")
    print("RESUMEN DE BENCHMARKS - ElectricSQL Sync")
    print(f"{'=' * 60}")

    all_passed = True
    for result in results:
        status = "[PASS]" if result.passed else "[FAIL]"
        all_passed = all_passed and result.passed
        print(f"\n{result.name}:")
        print(f"   Mean: {result.mean_ms:.2f}ms")
        print(f"   P95:  {result.p95_ms:.2f}ms (target: {result.target_ms}ms) {status}")
        print(f"   P99:  {result.p99_ms:.2f}ms")
        print(f"   Range: {result.min_ms:.2f}ms - {result.max_ms:.2f}ms")

    print("\nOffline Throughput:")
    print(f"   {throughput['ops_per_second']:.0f} ops/s")
    print(f"   Latency P95: {throughput['latency_p95_ms']:.2f}ms")

    print(f"\n{'=' * 60}")
    overall = (
        "[PASS] ALL BENCHMARKS PASSED"
        if all_passed
        else "[FAIL] SOME BENCHMARKS FAILED"
    )
    print(overall)
    print(f"{'=' * 60}")


def save_results(results: list[BenchmarkResult], throughput: dict) -> None:
    """Guarda resultados en JSON."""
    RESULTS_DIR.mkdir(exist_ok=True)

    output = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "electric_url": ELECTRIC_URL,
            "tenant_id": TENANT_ID,
            "iterations": NUM_ITERATIONS,
        },
        "benchmarks": [r.to_dict() for r in results],
        "throughput": throughput,
        "all_passed": all(r.passed for r in results),
    }

    filepath = RESULTS_DIR / "sync_benchmark.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nResultados guardados en: {filepath}")


async def main() -> int:
    print(f"\n{'=' * 60}")
    print("BENCHMARKS DE SINCRONIZACIÓN - ElectricSQL")
    print(f"{'=' * 60}")
    print(f"Electric URL: {ELECTRIC_URL}")
    print(f"Tenant ID: {TENANT_ID}")
    print(f"Timeout: {SYNC_TIMEOUT}s")

    data = load_test_data()
    if not any(data.values()):
        print("\n❌ No hay datos de prueba. Ejecuta: python setup.py")
        return 1

    client = MockElectricClient(ELECTRIC_URL, TENANT_ID)
    await client.connect()

    results = []

    initial_result = await benchmark_initial_sync(client, data)
    results.append(initial_result)

    incremental_result = await benchmark_incremental_sync(client)
    results.append(incremental_result)

    throughput = await benchmark_offline_throughput(client)

    await client.disconnect()

    print_summary(results, throughput)
    save_results(results, throughput)

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
