#!/usr/bin/env python3
"""
SPRINT 0: Cleanup y Validación Automática
Limpia deuda técnica y valida que todo esté listo para desarrollo

Uso: python cleanup_and_validate.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Colores
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
END = "\033[0m"

def log_section(title):
    """Log sección"""
    print(f"\n{BLUE}{'='*70}{END}")
    print(f"{BLUE}{title}{END}")
    print(f"{BLUE}{'='*70}{END}\n")

def log_ok(msg):
    """Log OK"""
    print(f"{GREEN}✓{END} {msg}")

def log_warning(msg):
    """Log warning"""
    print(f"{YELLOW}⚠{END} {msg}")

def log_error(msg):
    """Log error"""
    print(f"{RED}✗{END} {msg}")

def log_info(msg):
    """Log info"""
    print(f"{BLUE}ℹ{END} {msg}")

class Cleanup:
    def __init__(self):
        self.repo_root = Path.cwd()
        self.backend = self.repo_root / "apps" / "backend"
        self.changes = []
        self.errors = []

    def run_all(self):
        """Ejecutar todas las limpiezas"""
        log_section("SPRINT 0: CLEANUP Y VALIDACIÓN")
        
        self.cleanup_debt()
        self.cleanup_dev_files()
        self.cleanup_cache()
        self.cleanup_docs()
        self.validate_structure()
        self.create_summary()
        
        print(f"\n{BLUE}{'='*70}{END}")
        if self.errors:
            log_error(f"Completado con {len(self.errors)} errores")
            for err in self.errors:
                print(f"  {err}")
        else:
            log_ok(f"Completado sin errores - {len(self.changes)} cambios")
        print(f"{BLUE}{'='*70}{END}\n")

    def cleanup_debt(self):
        """Ejecutar cleanup scripts"""
        log_section("1. LIMPIAR DEUDA TÉCNICA")
        
        debt_scripts = [
            "cleanup_stuck_imports.py",
            "fix_duplicate_modules.py",
            "fix_pos_translations.py"
        ]
        
        for script in debt_scripts:
            path = self.repo_root / script
            if path.exists():
                log_info(f"Ejecutando {script}...")
                try:
                    result = subprocess.run(
                        [sys.executable, str(path)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0:
                        log_ok(f"{script} ejecutado")
                        self.changes.append(f"Executed {script}")
                    else:
                        log_warning(f"{script} falló: {result.stderr[:100]}")
                        self.errors.append(f"{script} failed")
                except Exception as e:
                    log_warning(f"Error ejecutando {script}: {e}")
                    self.errors.append(f"{script} exception: {e}")
            else:
                log_warning(f"{script} no encontrado")

    def cleanup_dev_files(self):
        """Eliminar archivos internos de dev"""
        log_section("2. ELIMINAR ARCHIVOS INTERNOS DE DEV")
        
        dev_files = [
            "find_byte.py",
            "find_spanish_identifiers.py",
            "analyze_excel.py",
            "check_db.py",
            "normalize_models.py",
            "test.db",
        ]
        
        for filename in dev_files:
            path = self.repo_root / filename
            if path.exists():
                try:
                    if path.is_file():
                        path.unlink()
                    else:
                        shutil.rmtree(path)
                    log_ok(f"Eliminado {filename}")
                    self.changes.append(f"Deleted {filename}")
                except Exception as e:
                    log_error(f"Error eliminando {filename}: {e}")
                    self.errors.append(f"Delete {filename}: {e}")
            else:
                log_info(f"{filename} no encontrado")

    def cleanup_cache(self):
        """Limpiar caché"""
        log_section("3. LIMPIAR CACHÉ")
        
        cache_dirs = [
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "htmlcov",
            ".coverage",
        ]
        
        for dirname in cache_dirs:
            for root in [self.repo_root, self.backend]:
                path = root / dirname
                if path.exists():
                    try:
                        if path.is_dir():
                            shutil.rmtree(path)
                        else:
                            path.unlink()
                        log_ok(f"Eliminado {path.relative_to(self.repo_root)}")
                        self.changes.append(f"Deleted {dirname}")
                    except Exception as e:
                        log_warning(f"Error limpiando {dirname}: {e}")

    def cleanup_docs(self):
        """Organizar documentación legacy"""
        log_section("4. ORGANIZAR DOCUMENTACIÓN LEGACY")
        
        legacy_docs = [
            "ARCHIVOS_CREADOS_FINAL.txt",
            "LISTO_100_PORCIENTO.txt",
            "LISTO_PARA_USAR.txt",
            "ENTREGA_FINAL.txt",
            "ENTREGA_FINAL_RETAIL_DASHBOARD.txt",
        ]
        
        docs_dir = self.repo_root / "docs"
        docs_dir.mkdir(exist_ok=True)
        
        for doc in legacy_docs:
            path = self.repo_root / doc
            if path.exists():
                try:
                    # Mover a docs/legacy/
                    legacy_dir = docs_dir / "legacy"
                    legacy_dir.mkdir(exist_ok=True)
                    dest = legacy_dir / doc
                    shutil.move(str(path), str(dest))
                    log_ok(f"Movido {doc} → docs/legacy/")
                    self.changes.append(f"Moved {doc} to docs/legacy/")
                except Exception as e:
                    log_warning(f"Error moviendo {doc}: {e}")

    def validate_structure(self):
        """Validar estructura del repo"""
        log_section("5. VALIDAR ESTRUCTURA")
        
        # Validar carpetas clave
        required_dirs = [
            "apps/backend",
            "apps/admin",
            "apps/tenant",
            "apps/packages",
            "ops",
            "docs",
        ]
        
        for dirname in required_dirs:
            path = self.repo_root / dirname
            if path.exists():
                log_ok(f"Encontrado {dirname}")
            else:
                log_error(f"Falta {dirname}")
                self.errors.append(f"Missing directory: {dirname}")

        # Validar archivos clave
        required_files = [
            "apps/backend/requirements.txt",
            "apps/admin/package.json",
            "apps/tenant/package.json",
            "apps/backend/pyproject.toml",
        ]
        
        for filename in required_files:
            path = self.repo_root / filename
            if path.exists():
                log_ok(f"Encontrado {filename}")
            else:
                log_error(f"Falta {filename}")
                self.errors.append(f"Missing file: {filename}")

    def create_summary(self):
        """Crear resumen"""
        log_section("6. CREAR RESUMEN")
        
        summary = f"""# SPRINT 0: CLEANUP SUMMARY

**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## ✅ Cambios Realizados

{len(self.changes)} cambios:
"""
        
        for change in self.changes:
            summary += f"- {change}\n"
        
        if self.errors:
            summary += f"\n## ⚠️ Errores/Warnings\n\n{len(self.errors)} items:\n"
            for error in self.errors:
                summary += f"- {error}\n"
        
        summary += f"""
## 🎯 Próximos Pasos

1. Revisar cambios: `git status`
2. Ver diferencias: `git diff`
3. Commit: `git add . && git commit -m "chore: sprint 0 cleanup"`
4. Proceder a MIÉRCOLES: Validar tests

## 📋 Checklist

- [x] Ejecutados cleanup_*.py scripts
- [x] Eliminados archivos de dev internos
- [x] Limpiado caché (.mypy_cache, etc)
- [x] Documentación legacy movida a docs/legacy/
- [x] Validada estructura del repo

## ⏭️ Siguiente

Ejecutar en terminal:
```bash
cd apps/backend
pip install -r requirements.txt
pytest --tb=short -q
```

Si todos los tests pasan: ✓ LISTO PARA SPRINT 1
"""
        
        summary_path = self.repo_root / "SPRINT_0_CLEANUP_SUMMARY.md"
        summary_path.write_text(summary)
        log_ok(f"Resumen guardado en SPRINT_0_CLEANUP_SUMMARY.md")


def main():
    """Main"""
    try:
        cleanup = Cleanup()
        cleanup.run_all()
        return 0
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Cancelado por usuario{END}")
        return 1
    except Exception as e:
        print(f"\n{RED}Error fatal: {e}{END}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
