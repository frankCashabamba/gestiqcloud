"""
Workers Celery para respaldo automatizado de base de datos.

Tareas:
- run_database_backup: Ejecuta el script de backup vía subprocess.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)

# Ruta al script de backup relativa al root del proyecto
_BACKUP_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "ops", "scripts", "backup.sh"
)


@shared_task(
    bind=True,
    max_retries=1,
    name="app.workers.backup_tasks.run_database_backup",
    queue="default",
)
def run_database_backup(self) -> dict[str, Any]:
    """
    Ejecuta el script de backup de PostgreSQL.
    Se ejecuta a las 02:00 UTC (Celery Beat schedule en celery_config.py).

    Returns:
        Diccionario con el resultado de la ejecución.
    """
    script_path = os.path.normpath(_BACKUP_SCRIPT)
    logger.info("Iniciando tarea: run_database_backup (%s)", script_path)

    if not os.path.isfile(script_path):
        logger.error("Script de backup no encontrado: %s", script_path)
        return {"status": "error", "detail": "backup script not found"}

    try:
        result = subprocess.run(
            ["bash", script_path],
            capture_output=True,
            text=True,
            timeout=3600,
        )

        if result.returncode == 0:
            logger.info("Backup completado exitosamente:\n%s", result.stdout)
            return {
                "status": "success",
                "returncode": result.returncode,
                "stdout": result.stdout,
            }

        logger.error(
            "Backup falló (exit code %d):\nstdout: %s\nstderr: %s",
            result.returncode,
            result.stdout,
            result.stderr,
        )
        return {
            "status": "error",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired:
        logger.error("Backup excedió el tiempo límite (3600s)")
        return {"status": "error", "detail": "backup timed out"}
    except Exception as err:
        logger.error("Error ejecutando backup: %s", err)
        return {"status": "error", "detail": str(err)}
