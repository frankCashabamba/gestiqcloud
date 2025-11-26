#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para completar la traducción del backend (últimas traducciones al 2%)
- Renombra directorios de módulos
- Traduce docstrings en schemas
- Traduce sector_defaults.py
- Traduce comentarios en models
- Renombra routers
- Traduce variables en workers
"""

import re
from pathlib import Path
from typing import Dict

BACKEND_PATH = Path(
    r"c:\Users\pc_cashabamba\Documents\GitHub\proyecto\apps\backend\app"
)

# Mapeos de traducción
MODULE_TRANSLATIONS = {
    "facturacion": "invoicing",
    "produccion": "production",
    "contabilidad": "accounting",
    "productos": "products",
    "compras": "purchases",
    "ventas": "sales",
}

ROUTER_TRANSLATIONS = {
    "categorias.py": "categories.py",
    "configuracionincial.py": "initial_config.py",
    "listadosgenerales.py": "general_listings.py",
}


def log_success(msg: str):
    print(f"[OK] {msg}")


def log_error(msg: str):
    print(f"[ERROR] {msg}")


def log_info(msg: str):
    print(f"[INFO] {msg}")


def log_warn(msg: str):
    print(f"[WARN] {msg}")


# ============================================================================
# PARTE 1: Renombrar directorios de módulos
# ============================================================================


def rename_modules():
    """Renombra directorios de módulos de español a inglés"""
    log_info("=" * 60)
    log_info("PARTE 1: Renombrando directorios de modulos")
    log_info("=" * 60)

    modules_path = BACKEND_PATH / "modules"

    for spanish, english in MODULE_TRANSLATIONS.items():
        spanish_path = modules_path / spanish
        english_path = modules_path / english

        if spanish_path.exists():
            if english_path.exists():
                log_warn(f"{spanish} -> {english}: {english} ya existe, saltando")
            else:
                try:
                    spanish_path.rename(english_path)
                    log_success(f"Renombrado: modules/{spanish}/ -> modules/{english}/")
                except Exception as e:
                    log_error(f"Error renombrando {spanish}: {e}")
        else:
            log_info(f"No encontrado: modules/{spanish}/ (quizas ya traducido)")


# ============================================================================
# PARTE 2: Traducir schemas y campos
# ============================================================================


def translate_file_content(filepath: Path, translations: Dict[str, str]) -> bool:
    """Traduce contenido de un archivo según un dict de reemplazos"""
    try:
        content = filepath.read_text(encoding="utf-8")
        original_content = content

        for spanish, english in translations.items():
            # Reemplazar en docstrings, comentarios y código
            content = re.sub(
                r"\b" + re.escape(spanish) + r"\b",
                english,
                content,
                flags=re.IGNORECASE,
            )

        if content != original_content:
            filepath.write_text(content, encoding="utf-8")
            return True
        return False
    except Exception as e:
        log_error(f"Error traduciendo {filepath.name}: {e}")
        return False


def translate_schemas():
    """Traduce docstrings y field aliases en schemas"""
    log_info("=" * 60)
    log_info("PARTE 2: Traduciendo schemas")
    log_info("=" * 60)

    schemas_path = BACKEND_PATH / "schemas"

    # Traducciones generales para schemas
    common_translations = {
        "documentacion": "documentation",
        "campo": "field",
        "campos": "fields",
        "configuracion": "configuration",
        "empresa": "company",
        "usuario": "user",
        "usuarios": "users",
        "nomina": "payroll",
        "empleado": "employee",
        "empleados": "employees",
        "descripcion": "description",
        "nombre": "name",
    }

    # finance_caja.py
    caja_file = schemas_path / "finance_caja.py"
    if caja_file.exists():
        if translate_file_content(caja_file, common_translations):
            log_success(f"Traducido: {caja_file.name}")
        else:
            log_info(f"Sin cambios: {caja_file.name}")

    # payroll.py
    payroll_file = schemas_path / "payroll.py"
    if payroll_file.exists():
        if translate_file_content(payroll_file, common_translations):
            log_success(f"Traducido: {payroll_file.name}")
        else:
            log_info(f"Sin cambios: {payroll_file.name}")

    # hr.py
    hr_file = schemas_path / "hr.py"
    if hr_file.exists():
        if translate_file_content(hr_file, common_translations):
            log_success(f"Traducido: {hr_file.name}")
        else:
            log_info(f"Sin cambios: {hr_file.name}")

    # configuracion.py
    config_file = schemas_path / "configuracion.py"
    if config_file.exists():
        if translate_file_content(config_file, common_translations):
            log_success(f"Traducido: {config_file.name}")
        else:
            log_info(f"Sin cambios: {config_file.name}")


# ============================================================================
# PARTE 3: Traducir sector_defaults.py
# ============================================================================


def translate_sector_defaults():
    """Traduce sector_defaults.py"""
    log_info("=" * 60)
    log_info("PARTE 3: Traduciendo services/sector_defaults.py")
    log_info("=" * 60)

    sector_file = BACKEND_PATH / "services" / "sector_defaults.py"
    if not sector_file.exists():
        log_warn(f"No encontrado: {sector_file}")
        return

    sector_translations = {
        "codigo": "code",
        "codigos": "codes",
        "nombre": "name",
        "nombres": "names",
        "descripcion": "description",
        "configuracion": "configuration",
        "predeterminado": "default",
        "predeterminados": "defaults",
        "activo": "active",
        "inactivo": "inactive",
        "tipo": "type",
        "tipos": "types",
    }

    if translate_file_content(sector_file, sector_translations):
        log_success("Traducido: sector_defaults.py")
    else:
        log_info("Sin cambios: sector_defaults.py")


# ============================================================================
# PARTE 4: Traducir comments en models
# ============================================================================


def translate_models():
    """Traduce comentarios en models"""
    log_info("=" * 60)
    log_info("PARTE 4: Traduciendo comentarios en models")
    log_info("=" * 60)

    models_path = BACKEND_PATH / "models"

    model_translations = {
        "empleado": "employee",
        "empleados": "employees",
        "gestion de caja": "cash management",
        "comentario": "comment",
        "comentarios": "comments",
        "estado": "status",
        "descripcion": "description",
        "fecha": "date",
        "fechas": "dates",
        "hora": "time",
        "horas": "hours",
    }

    # employee.py
    employee_file = models_path / "employee.py"
    if employee_file.exists():
        if translate_file_content(employee_file, model_translations):
            log_success("Traducido: employee.py")
        else:
            log_info("Sin cambios: employee.py")

    # cash_management.py
    cash_file = models_path / "cash_management.py"
    if cash_file.exists():
        if translate_file_content(cash_file, model_translations):
            log_success("Traducido: cash_management.py")
        else:
            log_info("Sin cambios: cash_management.py")


# ============================================================================
# PARTE 5: Renombrar routers
# ============================================================================


def rename_routers():
    """Renombra archivos routers de español a inglés"""
    log_info("=" * 60)
    log_info("PARTE 5: Renombrando routers")
    log_info("=" * 60)

    routers_path = BACKEND_PATH / "routers"

    for spanish, english in ROUTER_TRANSLATIONS.items():
        spanish_path = routers_path / spanish
        english_path = routers_path / english

        if spanish_path.exists():
            if english_path.exists():
                log_warn(f"{spanish} -> {english}: {english} ya existe, saltando")
            else:
                try:
                    spanish_path.rename(english_path)
                    log_success(f"Renombrado: routers/{spanish} -> routers/{english}")
                except Exception as e:
                    log_error(f"Error renombrando {spanish}: {e}")
        else:
            log_info(f"No encontrado: routers/{spanish} (quizas ya traducido)")


# ============================================================================
# PARTE 6: Traducir variables en workers
# ============================================================================


def translate_workers():
    """Traduce variables y docstrings en workers"""
    log_info("=" * 60)
    log_info("PARTE 6: Traduciendo workers")
    log_info("=" * 60)

    workers_path = BACKEND_PATH / "workers"

    worker_translations = {
        "notificacion": "notification",
        "notificaciones": "notifications",
        "factura": "invoice",
        "facturas": "invoices",
        "mensaje": "message",
        "mensajes": "messages",
        "estado": "status",
        "error": "error",
        "errores": "errors",
        "tarea": "task",
        "tareas": "tasks",
        "enviado": "sent",
        "recibido": "received",
    }

    # notifications.py
    notifications_file = workers_path / "notifications.py"
    if notifications_file.exists():
        if translate_file_content(notifications_file, worker_translations):
            log_success("Traducido: notifications.py")
        else:
            log_info("Sin cambios: notifications.py")

    # einvoicing_tasks.py
    einvoicing_file = workers_path / "einvoicing_tasks.py"
    if einvoicing_file.exists():
        if translate_file_content(einvoicing_file, worker_translations):
            log_success("Traducido: einvoicing_tasks.py")
        else:
            log_info("Sin cambios: einvoicing_tasks.py")


# ============================================================================
# PARTE 7: Actualizar imports (necesario después de renombrar directorios)
# ============================================================================


def update_imports_after_module_rename():
    """Actualiza imports en todo el codebase después de renombrar módulos"""
    log_info("=" * 60)
    log_info("PARTE 7: Actualizando imports")
    log_info("=" * 60)

    # Mapeo de imports antiguos a nuevos
    import_translations = {
        "from app.modules.facturacion": "from app.modules.invoicing",
        "from app.modules.produccion": "from app.modules.production",
        "from app.modules.contabilidad": "from app.modules.accounting",
        "from app.modules.productos": "from app.modules.products",
        "from app.modules.compras": "from app.modules.purchases",
        "from app.modules.ventas": "from app.modules.sales",
        "import app.modules.facturacion": "import app.modules.invoicing",
        "import app.modules.produccion": "import app.modules.production",
        "import app.modules.contabilidad": "import app.modules.accounting",
        "import app.modules.productos": "import app.modules.products",
        "import app.modules.compras": "import app.modules.purchases",
        "import app.modules.ventas": "import app.modules.sales",
    }

    changes = 0
    for py_file in BACKEND_PATH.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
            original = content

            for old, new in import_translations.items():
                content = content.replace(old, new)

            if content != original:
                py_file.write_text(content, encoding="utf-8")
                changes += 1
        except Exception as e:
            log_warn(f"Error actualizando {py_file.name}: {e}")

    if changes > 0:
        log_success(f"Actualizados {changes} archivos con imports nuevos")
    else:
        log_info("Sin cambios de imports necesarios")


# ============================================================================
# MAIN
# ============================================================================


def main():
    print("\n" + "=" * 70)
    print("COMPLETAR TRADUCCION DEL BACKEND (ULTIMAS TRADUCCIONES AL 2%)")
    print("=" * 70 + "\n")

    try:
        # Ejecutar todas las partes
        rename_modules()
        translate_schemas()
        translate_sector_defaults()
        translate_models()
        rename_routers()
        translate_workers()
        update_imports_after_module_rename()

        print("\n" + "=" * 70)
        print("TRADUCCION COMPLETADA CON EXITO")
        print("=" * 70 + "\n")

        print("PROXIMOS PASOS:")
        print("1. Revisar cambios: git diff")
        print("2. Ejecutar tests: pytest tests/ -v")
        print(
            "3. Hacer commit: git add . && git commit -m 'Complete Spanish to English refactoring'"
        )
        print()

    except Exception as e:
        log_error(f"Error general: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
