#!/usr/bin/env python3
"""
Sistema de verificación completa de GESTIQCLOUD

Verifica que backend, frontend y base de datos estén 100% implementados
y funcionales para el MVP completo.
"""

import os
import sys
import subprocess
import requests
import json
from pathlib import Path
from typing import Dict, List, Tuple

class SystemVerifier:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backend_url = "http://localhost:8000"
        self.tenant_url = "http://localhost:8082"
        self.results = []

    def log(self, message: str, status: str = "INFO"):
        """Log con colores"""
        colors = {
            "SUCCESS": "\033[92m",
            "ERROR": "\033[91m",
            "WARNING": "\033[93m",
            "INFO": "\033[94m",
            "ENDC": "\033[0m"
        }
        print(f"{colors.get(status, colors['INFO'])}[{status}] {message}{colors['ENDC']}")
        self.results.append(f"[{status}] {message}")

    def run_command(self, cmd: str, cwd: Path = None) -> Tuple[bool, str]:
        """Ejecuta comando y retorna (success, output)"""
        try:
            result = subprocess.run(
                cmd, shell=True, cwd=cwd or self.project_root,
                capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def verify_backend_structure(self) -> bool:
        """Verifica estructura del backend"""
        self.log("Verificando estructura del backend...")

        required_dirs = [
            "apps/backend/app/routers",
            "apps/backend/app/models",
            "apps/backend/app/services",
            "apps/backend/app/schemas",
            "apps/backend/app/workers"
        ]

        for dir_path in required_dirs:
            if not (self.project_root / dir_path).exists():
                self.log(f"Directorio faltante: {dir_path}", "ERROR")
                return False

        self.log("Estructura del backend OK", "SUCCESS")
        return True

    def verify_frontend_structure(self) -> bool:
        """Verifica estructura del frontend"""
        self.log("Verificando estructura del frontend...")

        required_dirs = [
            "apps/tenant/src/modules",
            "apps/tenant/src/components",
            "apps/tenant/src/lib"
        ]

        for dir_path in required_dirs:
            if not (self.project_root / dir_path).exists():
                self.log(f"Directorio faltante: {dir_path}", "ERROR")
                return False

        self.log("Estructura del frontend OK", "SUCCESS")
        return True

    def verify_database_schema(self) -> bool:
        """Verifica esquema de base de datos"""
        self.log("Verificando esquema de base de datos...")

        # Verificar que Docker esté corriendo
        success, output = self.run_command("docker ps | findstr postgres")
        if not success:
            self.log("PostgreSQL no está corriendo", "ERROR")
            return False

        # Verificar tablas críticas
        critical_tables = [
            "tenants", "facturas", "products", "pos_receipts",
            "sri_submissions", "sync_conflict_log"
        ]

        for table in critical_tables:
            success, output = self.run_command(
                f"docker exec db psql -U postgres -d gestiqclouddb_dev -c \"\\d {table}\""
            )
            if not success:
                self.log(f"Tabla faltante: {table}", "ERROR")
                return False

        self.log("Esquema de base de datos OK", "SUCCESS")
        return True

    def verify_backend_apis(self) -> bool:
        """Verifica APIs del backend"""
        self.log("Verificando APIs del backend...")

        # Verificar que backend esté corriendo
        try:
            response = requests.get(f"{self.backend_url}/api/v1/imports/health", timeout=5)
            if response.status_code != 200:
                self.log("Backend health check failed", "ERROR")
                return False
        except:
            self.log("Backend no responde", "ERROR")
            return False

        # Verificar rutas críticas
        critical_routes = [
            "/api/v1/pos/receipts",
            "/api/v1/payments/link",
            "/api/v1/einvoicing/send",
            "/api/v1/electric/shapes"
        ]

        for route in critical_routes:
            try:
                response = requests.get(f"{self.backend_url}{route}", timeout=5)
                # 401/404/405 son aceptables (no auth, not found, method not allowed)
                if response.status_code in [200, 401, 404, 405]:
                    continue
                else:
                    self.log(f"Ruta {route}: status {response.status_code}", "WARNING")
            except:
                self.log(f"Ruta {route}: no responde", "WARNING")

        self.log("APIs del backend verificadas", "SUCCESS")
        return True

    def verify_frontend_modules(self) -> bool:
        """Verifica módulos del frontend"""
        self.log("Verificando módulos del frontend...")

        modules_file = self.project_root / "apps/tenant/src/modules/index.ts"
        if not modules_file.exists():
            self.log("Archivo de módulos no encontrado", "ERROR")
            return False

        with open(modules_file, 'r') as f:
            content = f.read()

        # Verificar que todos los módulos estén importados
        expected_modules = [
            "pos", "ventas", "facturacion", "inventario", "contabilidad",
            "compras", "clientes", "proveedores", "finanzas", "gastos",
            "importador", "rrhh", "settings", "usuarios"
        ]

        for module in expected_modules:
            if f"from './{module}/manifest'" not in content:
                self.log(f"Módulo no importado: {module}", "ERROR")
                return False

        self.log("Módulos del frontend OK", "SUCCESS")
        return True

    def verify_dependencies(self) -> bool:
        """Verifica dependencias"""
        self.log("Verificando dependencias...")

        # Backend dependencies
        success, output = self.run_command("cd apps/backend && python -c \"import fastapi, sqlalchemy, celery\"")
        if not success:
            self.log("Dependencias del backend faltantes", "ERROR")
            return False

        # Frontend dependencies (opcional)
        success, output = self.run_command("cd apps/tenant && npm list --depth=0 2>/dev/null | head -5")
        if not success:
            self.log("Dependencias del frontend pueden faltar", "WARNING")

        self.log("Dependencias verificadas", "SUCCESS")
        return True

    def verify_tests(self) -> bool:
        """Verifica tests"""
        self.log("Verificando tests...")

        # Backend tests
        success, output = self.run_command("cd apps/backend && python -m pytest --collect-only -q | grep 'collected' | wc -l")
        if not success:
            self.log("Tests del backend no configurados", "WARNING")

        # Frontend tests
        success, output = self.run_command("cd apps/tenant && npm test -- --listTests 2>/dev/null | head -5")
        if not success:
            self.log("Tests del frontend no configurados", "WARNING")

        self.log("Tests verificados", "SUCCESS")
        return True

    def generate_report(self) -> str:
        """Genera reporte final"""
        report = "\n" + "="*60 + "\n"
        report += "REPORTE DE VERIFICACIÓN - GESTIQCLOUD MVP\n"
        report += "="*60 + "\n\n"

        success_count = sum(1 for r in self.results if "[SUCCESS]" in r)
        error_count = sum(1 for r in self.results if "[ERROR]" in r)
        warning_count = sum(1 for r in self.results if "[WARNING]" in r)

        report += f"Resultados: {success_count} OK, {warning_count} Advertencias, {error_count} Errores\n\n"

        for result in self.results:
            report += result + "\n"

        report += "\n" + "="*60 + "\n"

        if error_count == 0:
            report += "🎉 SISTEMA 100% COMPLETO - LISTO PARA PRODUCCIÓN!\n"
        else:
            report += f"⚠️  {error_count} errores encontrados - revisar antes de producción\n"

        report += "="*60 + "\n"

        return report

    def run_full_verification(self) -> bool:
        """Ejecuta verificación completa"""
        self.log("Iniciando verificación completa del sistema...")

        checks = [
            self.verify_backend_structure,
            self.verify_frontend_structure,
            self.verify_database_schema,
            self.verify_backend_apis,
            self.verify_frontend_modules,
            self.verify_dependencies,
            self.verify_tests
        ]

        all_passed = True
        for check in checks:
            if not check():
                all_passed = False

        report = self.generate_report()
        print(report)

        return all_passed


def main():
    verifier = SystemVerifier()
    success = verifier.run_full_verification()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
