#!/usr/bin/env python3
"""
Script de validación SPEC-1: ejecuta checks de compliance del módulo de imports.

Uso:
    python ops/scripts/validate_imports_spec1.py [--html] [--ci]

Opciones:
    --html: Genera reporte HTML en ops/reports/spec1_compliance.html
    --ci: Modo CI (exit code 1 si hay fallos)
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List


class ValidationResult:
    def __init__(
        self, name: str, passed: bool, message: str = "", details: List[str] = None
    ):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or []


def check_migrations() -> ValidationResult:
    """Verifica que migraciones de imports estén aplicadas."""
    try:
        result = subprocess.run(
            ["psql", "$DATABASE_URL", "-c", "SELECT 1 FROM import_batches LIMIT 1"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return ValidationResult("Migrations", True, "Todas las tablas presentes")
        else:
            return ValidationResult(
                "Migrations", False, "Tablas faltantes", [result.stderr]
            )
    except Exception as e:
        return ValidationResult("Migrations", False, f"Error: {e}")


def check_rls() -> ValidationResult:
    """Verifica que RLS esté habilitado."""
    try:
        result = subprocess.run(
            [
                "psql",
                "$DATABASE_URL",
                "-tA",
                "-c",
                "SELECT relname FROM pg_class WHERE relname IN ('import_batches', 'import_items') AND relrowsecurity = true",
            ],
            capture_output=True,
            text=True,
        )
        tables = result.stdout.strip().split("\n")
        if "import_batches" in tables and "import_items" in tables:
            return ValidationResult("RLS", True, "RLS habilitado en tablas críticas")
        else:
            return ValidationResult(
                "RLS", False, "RLS no habilitado", [f"Tablas encontradas: {tables}"]
            )
    except Exception as e:
        return ValidationResult("RLS", False, f"Error: {e}")


def check_tests() -> ValidationResult:
    """Ejecuta tests del módulo imports."""
    try:
        result = subprocess.run(
            ["pytest", "apps/backend/tests/modules/imports/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        if result.returncode == 0:
            return ValidationResult("Tests", True, "Todos los tests pasaron")
        else:
            failures = [line for line in result.stdout.split("\n") if "FAILED" in line]
            return ValidationResult(
                "Tests", False, f"{len(failures)} tests fallidos", failures[:5]
            )
    except Exception as e:
        return ValidationResult("Tests", False, f"Error: {e}")


def check_golden_tests() -> ValidationResult:
    """Verifica golden tests."""
    try:
        result = subprocess.run(
            [
                "pytest",
                "apps/backend/tests/modules/imports/golden/",
                "-m",
                "golden",
                "-v",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        if result.returncode == 0:
            return ValidationResult("Golden Tests", True, "Outputs consistentes")
        else:
            return ValidationResult("Golden Tests", False, "Golden outputs difieren")
    except Exception as e:
        return ValidationResult("Golden Tests", False, f"Error: {e}")


def check_benchmarks() -> ValidationResult:
    """Verifica benchmarks de performance."""
    bench_dir = (
        Path(__file__).parent.parent.parent
        / "apps/backend/tests/modules/imports/benchmark"
    )

    # Ejecutar bench_validation (más rápido)
    try:
        subprocess.run(
            ["python", str(bench_dir / "bench_validation.py")],
            capture_output=True,
            text=True,
            cwd=bench_dir,
        )

        # Parsear resultados JSON
        json_files = list(bench_dir.glob("bench_validation_results_*.json"))
        if json_files:
            latest = max(json_files, key=lambda p: p.stat().st_mtime)
            with open(latest) as f:
                data = json.load(f)

            passed = all(b.get("passed", False) for b in data["benchmarks"])
            if passed:
                return ValidationResult(
                    "Benchmarks", True, "Targets de performance cumplidos"
                )
            else:
                failures = [
                    b["test"] for b in data["benchmarks"] if not b.get("passed")
                ]
                return ValidationResult(
                    "Benchmarks", False, "Algunos benchmarks fallaron", failures
                )
        else:
            return ValidationResult("Benchmarks", False, "No se generaron resultados")
    except Exception as e:
        return ValidationResult("Benchmarks", False, f"Error: {e}")


def check_security() -> ValidationResult:
    """Verifica configuración de seguridad."""
    checks = []

    # ClamAV config
    from app.core.config import settings

    if hasattr(settings, "CLAMAV_ENABLED") and settings.CLAMAV_ENABLED:
        checks.append("✅ ClamAV habilitado")
    else:
        checks.append("⚠️  ClamAV deshabilitado (opcional en dev)")

    # Límites de tamaño
    if hasattr(settings, "MAX_UPLOAD_SIZE_MB"):
        checks.append(f"✅ Max upload: {settings.MAX_UPLOAD_SIZE_MB} MB")

    # S3 encryption
    if hasattr(settings, "S3_ENCRYPT"):
        checks.append("✅ S3 encryption configurado")

    return ValidationResult("Security", True, "Configuración validada", checks)


def check_metrics() -> ValidationResult:
    """Verifica que métricas estén expuestas."""
    try:
        import requests

        response = requests.get("http://localhost:8000/metrics", timeout=5)
        if response.status_code == 200:
            metrics_text = response.text
            required = [
                "imports_batches_created_total",
                "imports_items_processed_total",
            ]
            found = [m for m in required if m in metrics_text]
            if len(found) == len(required):
                return ValidationResult(
                    "Metrics", True, "Métricas de imports disponibles"
                )
            else:
                missing = set(required) - set(found)
                return ValidationResult(
                    "Metrics", False, "Métricas faltantes", list(missing)
                )
        else:
            return ValidationResult(
                "Metrics",
                False,
                f"Endpoint /metrics no disponible (status {response.status_code})",
            )
    except Exception as e:
        return ValidationResult("Metrics", False, f"Error: {e}")


def generate_html_report(results: List[ValidationResult], output_path: Path):
    """Genera reporte HTML."""
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    compliance_pct = (passed_count / total_count * 100) if total_count > 0 else 0

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SPEC-1 Compliance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f0f0f0; padding: 20px; border-radius: 8px; }}
        .result {{ margin: 20px 0; padding: 15px; border-left: 4px solid; }}
        .passed {{ border-color: #4CAF50; background: #f1f8f4; }}
        .failed {{ border-color: #f44336; background: #fef1f0; }}
        .details {{ margin-top: 10px; font-size: 0.9em; color: #666; }}
        .progress {{ width: 100%; height: 30px; background: #e0e0e0; border-radius: 15px; }}
        .progress-bar {{ height: 100%; background: #4CAF50; border-radius: 15px; text-align: center; color: white; line-height: 30px; }}
    </style>
</head>
<body>
    <h1>📊 SPEC-1 Compliance Report</h1>
    <p><strong>Fecha:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

    <div class="summary">
        <h2>Resumen</h2>
        <p><strong>Compliance:</strong> {passed_count}/{total_count} checks pasados</p>
        <div class="progress">
            <div class="progress-bar" style="width: {compliance_pct}%">{compliance_pct:.0f}%</div>
        </div>
    </div>

    <h2>Resultados detallados</h2>
"""

    for result in results:
        status_class = "passed" if result.passed else "failed"
        status_icon = "✅" if result.passed else "❌"

        html += f"""
    <div class="result {status_class}">
        <h3>{status_icon} {result.name}</h3>
        <p>{result.message}</p>
"""
        if result.details:
            html += '<div class="details"><ul>'
            for detail in result.details:
                html += f"<li>{detail}</li>"
            html += "</ul></div>"

        html += "    </div>\n"

    html += """
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"📄 Reporte HTML generado: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Valida compliance de SPEC-1")
    parser.add_argument("--html", action="store_true", help="Genera reporte HTML")
    parser.add_argument(
        "--ci", action="store_true", help="Modo CI (exit code 1 si fallos)"
    )
    args = parser.parse_args()

    print("🔍 Validando SPEC-1 Compliance...\n")

    checks = [
        ("Migraciones", check_migrations),
        ("RLS", check_rls),
        ("Tests", check_tests),
        ("Golden Tests", check_golden_tests),
        ("Benchmarks", check_benchmarks),
        ("Security", check_security),
        ("Metrics", check_metrics),
    ]

    results: List[ValidationResult] = []

    for name, check_func in checks:
        print(f"▶️  Checking {name}...")
        result = check_func()
        results.append(result)

        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"   {status}: {result.message}")
        if result.details:
            for detail in result.details[:3]:
                print(f"     - {detail}")
        print()

    # Resumen
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    compliance_pct = (passed / total * 100) if total > 0 else 0

    print("=" * 60)
    print(f"COMPLIANCE: {passed}/{total} ({compliance_pct:.0f}%)")
    print("=" * 60)

    # Generar HTML si solicitado
    if args.html:
        report_path = Path(__file__).parent.parent / "reports" / "spec1_compliance.html"
        generate_html_report(results, report_path)

    # Exit code para CI
    if args.ci and passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
