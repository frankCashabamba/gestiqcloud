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
from app.models import GlobalActionPermission

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Ejecutar todos los seeds"""
    db = SessionLocal()

    try:
        logger.info("Starting seeds...")

        # NOTA: Los sector templates se cargan via migración SQL
        # Ver: ops/migrations/2025-11-29_001_migrate_sector_templates_to_db/
        logger.info("Sector templates loaded from SQL migration")

        pos_permissions = [
            {"key": "pos.view", "module": "pos", "description": "Access POS module"},
            {"key": "pos.register.read", "module": "pos", "description": "Read POS registers"},
            {"key": "pos.register.manage", "module": "pos", "description": "Manage POS registers"},
            {"key": "pos.shift.read", "module": "pos", "description": "Read POS shifts"},
            {"key": "pos.shift.open", "module": "pos", "description": "Open POS shifts"},
            {"key": "pos.shift.close", "module": "pos", "description": "Close POS shifts"},
            {"key": "pos.receipt.read", "module": "pos", "description": "Read POS receipts"},
            {"key": "pos.receipt.create", "module": "pos", "description": "Create POS receipts"},
            {"key": "pos.receipt.pay", "module": "pos", "description": "Pay POS receipts"},
            {"key": "pos.receipt.refund", "module": "pos", "description": "Refund POS receipts"},
            {"key": "pos.receipt.print", "module": "pos", "description": "Print POS receipts"},
            {"key": "pos.receipt.manage", "module": "pos", "description": "Manage POS receipts"},
            {"key": "pos.reports.view", "module": "pos", "description": "View POS reports"},
            {"key": "pos.analytics.view", "module": "pos", "description": "View POS analytics"},
        ]

        existing_keys = {
            row[0]
            for row in db.query(GlobalActionPermission.key).filter(
                GlobalActionPermission.key.in_([p["key"] for p in pos_permissions])
            )
        }
        to_create = [p for p in pos_permissions if p["key"] not in existing_keys]
        if to_create:
            db.add_all(GlobalActionPermission(**p) for p in to_create)
            db.commit()
            logger.info("Seeded POS permissions: %s", len(to_create))
        else:
            logger.info("POS permissions already present")

        logger.info("Seeds completed")
        return 0

    except Exception as e:
        logger.error("Seed error: %s", e, exc_info=True)
        db.rollback()
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
