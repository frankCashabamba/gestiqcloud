#!/usr/bin/env python
"""
Script para ejecutar todos los seeds de la aplicación.

Uso:
    python scripts/run_seeds.py
"""

import logging
import sys
from pathlib import Path

# Agregar la carpeta app al path
app_root = Path(__file__).parent.parent
sys.path.insert(0, str(app_root.parent))

from app.config.database import SessionLocal

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Ejecutar todos los seeds"""
    db = SessionLocal()

    try:
        logger.info("🌱 Iniciando seeds...")

        # NOTA: Los sector templates se cargan via migración SQL
        # Ver: ops/migrations/2025-11-29_001_migrate_sector_templates_to_db/
        logger.info("✓ Sector templates cargados desde migración SQL")

        logger.info("✅ Todos los seeds completados exitosamente")
        return 0

    except Exception as e:
        logger.error(f"❌ Error durante seeds: {e}", exc_info=True)
        db.rollback()
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
