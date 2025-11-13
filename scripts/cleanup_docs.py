#!/usr/bin/env python3
"""
Script de limpieza de documentación - GestiQCloud
Elimina archivos temporales, backups y reorganiza documentación
"""

import shutil
from pathlib import Path

# Directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent

# Archivos a eliminar
FILES_TO_DELETE = [
    # Backups (.bak)
    "AGENTS.md.bak",
    "RLS_IMPLEMENTATION_SUMMARY.md.bak",
    "README_EXECUTIVE_SUMMARY.md.bak",
    "PRODUCT_IMPORT_GUIDE.md.bak",
    "TENANT_MIGRATION_GUIDE.md.bak",
    "TENANT_CONSOLIDATION_SUMMARY.md.bak",
    "ONBOARDING_AUTOMATICO.md.bak",
    "MODULE_STATUS_REPORT.md.bak",
    "MIGRATION_PLAN.md.bak",
    "MIGRACION_UUID_RESUMEN.md.bak",
    "IMPORTS_IMPLEMENTATION_COMPLETE.md.bak",
    "TENANT_MIGRATION_IMPORTS_SUMMARY.md.bak",
    "tmp_out_2.txt.bak",
    "tmp_out_1.txt.bak",
    "tmp_chunk.txt.bak",
    # Temporales (.txt)
    "tmp_chunk.txt",
    "tmp_out_1.txt",
    "tmp_out_2.txt",
    "tmp_numbered.txt",
    "tmp_num_tenant.txt",
    "tmp_num_uc.txt",
    "test_results.txt",
    "failed_summary.txt",
    # Backups de código
    "backAGENTS.md",
    "backAGENTS_SPEC_ORIGINAL.md",
    # Scripts temporales
    "tmp_dummy.py",
    "tmp_try_import.py",
    "analyze_excel.py",
    "check_completion.py",
    "verify_system.py",
    "test_product_import.py",
    # Base de datos temporal
    "test.db",
    "$null",
    # HTML temporal
    "pricing_core_plantillas.html",
    # Documentación obsoleta
    "MIGRACION_UUID_RESUMEN.md",
    "RLS_IMPLEMENTATION_SUMMARY.md",
    "TENANT_CONSOLIDATION_SUMMARY.md",
    "TENANT_MIGRATION_GUIDE.md",
    "TENANT_MIGRATION_IMPORTS_SUMMARY.md",
    "SECURITY_GUARDS_SUMMARY.md",
    "README_EXECUTIVE_SUMMARY.md",
    "IMPORTS_SPEC1_FINAL_SUMMARY.md",
    "IMPORTS_CELERY_SUMMARY.md",
    "IMPORTS_IMPLEMENTATION_COMPLETE.md",
    "IMPLEMENTATION_COMPLETE.md",
    "FINAL_SUMMARY.md",
    "INTEGRATION_COMPLETE.md",
    "MODULE_STATUS_REPORT.md",
    "PROMPTS.md",
    # Dumps
    "dump_local.pgcustom",
]

# Archivos a mover a docs/
FILES_TO_MOVE = {
    "README_DEV.md": "docs/development/README_DEV.md",
    "README_DB.md": "docs/development/DATABASE.md",
    "DATABASE_SETUP_GUIDE.md": "docs/development/DATABASE_SETUP.md",
    "TROUBLESHOOTING_DOCKER.md": "docs/development/DOCKER_TROUBLESHOOTING.md",
    "FRONTEND_COVERAGE_PLAN.md": "docs/development/FRONTEND_COVERAGE.md",
    "MIGRATION_PLAN.md": "docs/migrations/MIGRATION_PLAN.md",
    "OFFLINE_ONLINE_TESTING.md": "docs/architecture/OFFLINE_SYNC.md",
    "PRODUCT_IMPORT_GUIDE.md": "docs/guides/PRODUCT_IMPORT.md",
    "ONBOARDING_AUTOMATICO.md": "docs/guides/ONBOARDING.md",
    "SETUP_AND_TEST.md": "docs/guides/SETUP_AND_TEST.md",
    "POS_MODULE_COMPLETE.md": "docs/modules/POS.md",
    "MODELS_UUID_MIGRATION_ANALYSIS.md": "docs/migrations/UUID_ANALYSIS.md",
    "MODELS_UUID_MIGRATION_COMPLETE.md": "docs/migrations/UUID_COMPLETE.md",
    "CLEANUP_PLAN.md": "docs/maintenance/CLEANUP_PLAN.md",
}


def main():
    """Ejecuta la limpieza completa"""
    print("🧹 Iniciando limpieza de documentación...")
    print(f"📁 Directorio: {PROJECT_ROOT}\n")

    deleted_count = 0
    moved_count = 0
    error_count = 0

    # 1. Eliminar archivos
    print("📝 Fase 1: Eliminando archivos obsoletos...")
    for filename in FILES_TO_DELETE:
        file_path = PROJECT_ROOT / filename
        if file_path.exists():
            try:
                if file_path.is_file():
                    file_path.unlink()
                    print(f"  ✅ Eliminado: {filename}")
                    deleted_count += 1
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
                    print(f"  ✅ Eliminado directorio: {filename}")
                    deleted_count += 1
            except Exception as e:
                print(f"  ❌ Error eliminando {filename}: {e}")
                error_count += 1
        else:
            print(f"  ⏭️  No existe: {filename}")

    # 2. Crear estructura docs/
    print("\n📂 Fase 2: Creando estructura docs/...")
    docs_structure = [
        "docs/development",
        "docs/architecture",
        "docs/migrations",
        "docs/modules",
        "docs/guides",
        "docs/maintenance",
    ]

    for directory in docs_structure:
        dir_path = PROJECT_ROOT / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ Creado: {directory}")

    # 3. Mover archivos
    print("\n📦 Fase 3: Moviendo archivos a docs/...")
    for source, destination in FILES_TO_MOVE.items():
        source_path = PROJECT_ROOT / source
        dest_path = PROJECT_ROOT / destination

        if source_path.exists():
            try:
                # Crear directorio destino si no existe
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                # Mover archivo
                shutil.move(str(source_path), str(dest_path))
                print(f"  ✅ Movido: {source} → {destination}")
                moved_count += 1
            except Exception as e:
                print(f"  ❌ Error moviendo {source}: {e}")
                error_count += 1
        else:
            print(f"  ⏭️  No existe: {source}")

    # 4. Resumen
    print("\n" + "=" * 60)
    print("✨ LIMPIEZA COMPLETADA")
    print("=" * 60)
    print("📊 Estadísticas:")
    print(f"  - Archivos eliminados: {deleted_count}")
    print(f"  - Archivos movidos: {moved_count}")
    print(f"  - Errores: {error_count}")
    print("\n📁 Archivos restantes en raíz:")

    # Listar archivos .md restantes en raíz
    remaining_docs = list(PROJECT_ROOT.glob("*.md"))
    for doc in sorted(remaining_docs):
        print(f"  - {doc.name}")

    print("\n✅ Limpieza finalizada correctamente!")
    print("📝 Próximo paso: Revisar y actualizar README.md y AGENTS.md")


if __name__ == "__main__":
    main()
