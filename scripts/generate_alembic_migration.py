#!/usr/bin/env python3
"""
Script para generar una migración Alembic para cambios de columnas.
Ejecutar: python generate_alembic_migration.py
"""

from datetime import datetime
from pathlib import Path

# CONFIGURAR AQUÍ - tabla y cambios de columnas
MIGRATIONS = {
    # "tabla_name": {
    #     "column_old": "column_new",
    #     "nombre": "name",
    #     "descripcion": "description",
    # },
}

ALEMBIC_DIR = Path(__file__).parent.parent / "apps" / "backend" / "alembic" / "versions"


def generate_migration(table_name: str, column_mappings: dict) -> str:
    """Generar el código de migración."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    migration_name = f"{timestamp}_rename_{table_name}_fields_to_english.py"

    # Generar las operaciones
    down_ops = []
    up_ops = []

    for old_col, new_col in column_mappings.items():
        # UP (aplicar cambios)
        up_ops.append(
            f"    op.alter_column('{table_name}', '{old_col}', new_column_name='{new_col}')"
        )
        # DOWN (revertir)
        down_ops.append(
            f"    op.alter_column('{table_name}', '{new_col}', new_column_name='{old_col}')"
        )

    template = f'''"""Rename {table_name} fields to English

Revision ID: {timestamp}
Revises:
Create Date: {datetime.now().isoformat()}

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '{timestamp}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Aplicar cambios."""
{chr(10).join(up_ops)}


def downgrade() -> None:
    """Revertir cambios."""
{chr(10).join(down_ops)}
'''

    return migration_name, template


def main():
    """Generar migraciones."""
    if not MIGRATIONS:
        print("❌ ERROR: MIGRATIONS está vacío")
        print("   Configura los cambios en la parte superior del script")
        return

    print("\n📋 Migraciones a generar:")

    for table_name, columns in MIGRATIONS.items():
        migration_name, content = generate_migration(table_name, columns)
        output_path = ALEMBIC_DIR / migration_name

        print(f"\n   📄 {migration_name}")
        print(f"      Tabla: {table_name}")
        print(f"      Cambios: {len(columns)}")
        for old, new in columns.items():
            print(f"        • {old} → {new}")

        # Escribir archivo
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        print(f"      ✅ Guardado en: {output_path.relative_to(Path.cwd())}")

    print(f"\n{'='*60}")
    print("⚠️  Próximos pasos:")
    print(f"   1. Revisar los archivos generados en {ALEMBIC_DIR}")
    print("   2. Ajustar down_revision con el ID de la migración anterior")
    print("   3. Ejecutar: alembic upgrade head")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
