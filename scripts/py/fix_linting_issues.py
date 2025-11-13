#!/usr/bin/env python3
"""
Script para corregir problemas sistemáticos de linting/type checking.
Ejecutar: python scripts/py/fix_linting_issues.py
"""

import os
import re
from pathlib import Path


def fix_me_py():
    """Corrige anotaciones de tipo en me.py"""
    path = Path("apps/backend/app/api/v1/me.py")
    content = path.read_text(encoding="utf-8")

    # Agregar tipo Dict[str, Any] al parámetro s
    content = content.replace(
        "def me(s = Depends(require_tenant)):",
        "def me(s: dict = Depends(require_tenant)) -> dict:",
    )

    path.write_text(content, encoding="utf-8")
    print(f"[OK] Fixed {path}")


def remove_empresa_references():
    """Elimina referencias a la clase Empresa eliminada"""
    files = [
        "apps/backend/app/modules/modulos/interface/http/admin.py",
        "apps/backend/app/modules/settings/interface/http/tenant.py",
        "apps/backend/app/routers/tenant/roles.py",
        "apps/backend/app/modules/modulos/interface/http/public.py",
    ]

    for file_path in files:
        p = Path(file_path)
        if not p.exists():
            continue

        content = p.read_text(encoding="utf-8")

        # Eliminar imports de Empresa
        content = re.sub(
            r"from app\.models\.empresa\.empresa import Empresa\n", "", content
        )

        p.write_text(content, encoding="utf-8")
        print(f"✅ Removed Empresa import from {p}")


def fix_rls_import():
    """Corrige import faltante de app.middleware.rls"""
    path = Path("apps/backend/app/routers/tenant/roles.py")
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")

    # Reemplazar el import incorrecto
    content = content.replace(
        "from app.middleware.rls import ensure_rls", "from app.db.rls import ensure_rls"
    )

    path.write_text(content, encoding="utf-8")
    print(f"✅ Fixed RLS import in {path}")


def clean_unused_imports_in_models_init():
    """Limpia imports no usados en models/__init__.py"""
    path = Path("apps/backend/app/models/__init__.py")
    if not path.exists():
        return

    # Los imports están ahí para que SQLAlchemy los registre
    # Solo removemos líneas excesivamente largas dividiéndolas
    content = path.read_text(encoding="utf-8")

    # Dividir línea larga de facturacion
    old_facturacion = "from app.models.core.facturacion import BankAccount, BankTransaction, InternalTransfer, Invoice, InvoiceTemp, MovimientoEstado, MovimientoTipo, Payment"
    new_facturacion = """from app.models.core.facturacion import (
    BankAccount, BankTransaction, InternalTransfer, Invoice,
    InvoiceTemp, MovimientoEstado, MovimientoTipo, Payment
)"""

    # Dividir línea larga de empresa
    old_empresa = "from app.models.empresa.empresa import CategoriaEmpresa, DiaSemana, HorarioAtencion, Idioma, Moneda, PerfilUsuario, PermisoAccionGlobal, RolBase, SectorPlantilla, TipoEmpresa, TipoNegocio"
    new_empresa = """from app.models.empresa.empresa import (
    CategoriaEmpresa, DiaSemana, HorarioAtencion, Idioma, Moneda,
    PerfilUsuario, PermisoAccionGlobal, RolBase, SectorPlantilla,
    TipoEmpresa, TipoNegocio
)"""

    content = content.replace(old_facturacion, new_facturacion)
    content = content.replace(old_empresa, new_empresa)

    # Agregar newline final
    if not content.endswith("\n"):
        content += "\n"

    path.write_text(content, encoding="utf-8")
    print(f"✅ Cleaned imports in {path}")


def fix_utcnow_deprecation():
    """Reemplaza datetime.utcnow() por datetime.now(datetime.timezone.utc)"""
    files = [
        "apps/backend/app/models/core/modelsimport.py",
        "apps/backend/app/models/tenant.py",
    ]

    for file_path in files:
        p = Path(file_path)
        if not p.exists():
            continue

        content = p.read_text(encoding="utf-8")

        # Asegurar import de timezone
        if "from datetime import" in content and "timezone" not in content:
            content = content.replace(
                "from datetime import datetime",
                "from datetime import datetime, timezone",
            )

        # Reemplazar utcnow()
        content = re.sub(r"datetime\.utcnow\(\)", "datetime.now(timezone.utc)", content)

        p.write_text(content, encoding="utf-8")
        print(f"✅ Fixed utcnow() deprecation in {p}")


def add_module_docstrings():
    """Añade docstrings de módulo donde faltan"""
    # Solo para módulos críticos
    critical_files = [
        ("apps/backend/app/models/__init__.py", "Model registry"),
        ("apps/backend/app/modules/crud.py", "CRUD operations"),
    ]

    for file_path, description in critical_files:
        p = Path(file_path)
        if not p.exists():
            continue

        content = p.read_text(encoding="utf-8")

        # Si no empieza con docstring, agregar
        if not content.startswith('"""') and not content.startswith("'''"):
            if content.startswith("#"):
                # Reemplazar comentario con docstring
                content = re.sub(r"^# .+\n", f'"""{description}"""\n', content)
            else:
                # Agregar al inicio
                content = f'"""{description}"""\n' + content

            p.write_text(content, encoding="utf-8")
            print(f"✅ Added docstring to {p}")


def fix_empresa_undefined():
    """Corrige errores de Empresa undefined en archivos específicos"""
    # En public.py - eliminar tipo Empresa
    path = Path("apps/backend/app/modules/modulos/interface/http/public.py")
    if path.exists():
        content = path.read_text(encoding="utf-8")
        # Cambiar tipo Empresa a Any o eliminar anotación
        content = re.sub(r": Empresa =", "=", content)
        path.write_text(content, encoding="utf-8")
        print(f"✅ Fixed Empresa type in {path}")


def main():
    """Ejecuta todas las correcciones"""
    print("Iniciando correcciones de linting...\n")

    os.chdir(Path(__file__).parent.parent.parent)

    fix_me_py()
    remove_empresa_references()
    fix_rls_import()
    clean_unused_imports_in_models_init()
    fix_utcnow_deprecation()
    add_module_docstrings()
    fix_empresa_undefined()

    print("\nCorrecciones completadas")
    print("\nProximos pasos:")
    print("1. Ejecutar: ruff check --fix apps/backend/")
    print("2. Ejecutar: mypy apps/backend/app")
    print("3. Revisar diagnostics restantes")


if __name__ == "__main__":
    main()
