"""
Benchmark OCR: medir latencia de Tesseract con diferentes configuraciones.
Target: P95 < 5s con 2 CPU cores.
"""

import json
import statistics
import time
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "documents"


def benchmark_tesseract_single_page(iterations: int = 10) -> dict[str, Any]:
    """
    Benchmark Tesseract en PDF single-page.
    """
    from app.modules.imports.application.photo_utils import extract_text_from_pdf

    pdf_path = FIXTURES_DIR / "factura_ec_sample.pdf"

    if not pdf_path.exists():
        return {"error": "Fixture no encontrado"}

    latencies: list[float] = []

    for i in range(iterations):
        start = time.perf_counter()

        with open(pdf_path, "rb") as f:
            text = extract_text_from_pdf(f.read())

        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

        print(f"  Iter {i + 1}/{iterations}: {elapsed:.3f}s (length: {len(text)} chars)")

    return {
        "test": "tesseract_single_page",
        "iterations": iterations,
        "mean_ms": statistics.mean(latencies) * 1000,
        "median_ms": statistics.median(latencies) * 1000,
        "p95_ms": sorted(latencies)[int(0.95 * len(latencies))] * 1000,
        "min_ms": min(latencies) * 1000,
        "max_ms": max(latencies) * 1000,
        "target_p95_ms": 5000,
        "passed": sorted(latencies)[int(0.95 * len(latencies))] < 5.0,
    }


def benchmark_image_preprocessing(iterations: int = 20) -> dict[str, Any]:
    """
    Benchmark mejora de imagen (deskew + denoise).
    Target: < 500ms por imagen.
    """
    from PIL import Image

    from app.modules.imports.application.photo_utils import denoise_image, deskew_image

    # Crear imagen sintética 1200x900 (típico de foto móvil)
    img = Image.new("RGB", (1200, 900), color=(255, 255, 255))

    latencies: list[float] = []

    for i in range(iterations):
        start = time.perf_counter()

        deskewed = deskew_image(img)
        denoised = denoise_image(deskewed)  # noqa: F841

        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

    return {
        "test": "image_preprocessing",
        "iterations": iterations,
        "mean_ms": statistics.mean(latencies) * 1000,
        "median_ms": statistics.median(latencies) * 1000,
        "p95_ms": sorted(latencies)[int(0.95 * len(latencies))] * 1000,
        "target_p95_ms": 500,
        "passed": sorted(latencies)[int(0.95 * len(latencies))] < 0.5,
    }


def benchmark_ocr_caching(iterations: int = 5) -> dict[str, Any]:
    """
    Verifica que caché de OCR funcione (segunda llamada debe ser instantánea).
    """
    from app.modules.imports.application.photo_utils import extract_text_from_pdf

    pdf_path = FIXTURES_DIR / "factura_ec_sample.pdf"

    with open(pdf_path, "rb") as f:
        pdf_content = f.read()

    # Primera llamada (sin cache)
    start = time.perf_counter()
    text1 = extract_text_from_pdf(pdf_content, file_sha="bench_cache_test")  # noqa: F841
    first_call = time.perf_counter() - start

    # Subsecuentes (con cache)
    cached_latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        text2 = extract_text_from_pdf(pdf_content, file_sha="bench_cache_test")  # noqa: F841
        cached_latencies.append(time.perf_counter() - start)

    avg_cached = statistics.mean(cached_latencies)
    speedup = first_call / avg_cached if avg_cached > 0 else 0

    return {
        "test": "ocr_caching",
        "first_call_ms": first_call * 1000,
        "cached_avg_ms": avg_cached * 1000,
        "speedup": speedup,
        "target_speedup": 10,
        "passed": speedup >= 10,
    }


def run_all_benchmarks() -> dict[str, Any]:
    """Ejecuta todos los benchmarks y genera reporte."""
    import datetime

    print("🔥 Running OCR benchmarks...\n")

    results = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "benchmarks": [],
    }

    # Tesseract single page
    print("1️⃣  Tesseract single-page...")
    results["benchmarks"].append(benchmark_tesseract_single_page(iterations=10))

    # Image preprocessing
    print("\n2️⃣  Image preprocessing...")
    results["benchmarks"].append(benchmark_image_preprocessing(iterations=20))

    # Caching
    print("\n3️⃣  OCR caching...")
    results["benchmarks"].append(benchmark_ocr_caching(iterations=5))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for bench in results["benchmarks"]:
        status = "✅ PASS" if bench.get("passed", False) else "❌ FAIL"
        test_name = bench["test"]

        if "p95_ms" in bench:
            print(
                f"{status} {test_name}: P95={bench['p95_ms']:.1f}ms (target: {bench.get('target_p95_ms')}ms)"
            )
        elif "speedup" in bench:
            print(
                f"{status} {test_name}: Speedup={bench['speedup']:.1f}x (target: {bench.get('target_speedup')}x)"
            )

    return results


if __name__ == "__main__":
    results = run_all_benchmarks()

    # Guardar resultados
    output_path = Path(__file__).parent / f"bench_ocr_results_{int(time.time())}.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📊 Results saved to: {output_path}")
