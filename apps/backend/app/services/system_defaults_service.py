"""System defaults service — lee/escribe configuraciones globales del sistema."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_DEFAULTS: list[dict[str, Any]] = [
    {
        "key": "reports.low_stock_threshold",
        "category": "reports",
        "value_text": "10",
        "value_type": "number",
        "description": "Umbral de stock bajo en reportes de inventario",
    },
    {
        "key": "invoicing.default_due_days",
        "category": "invoicing",
        "value_text": "30",
        "value_type": "number",
        "description": "Días de vencimiento por defecto en nuevas facturas",
    },
    {
        "key": "tax.fallback_rate",
        "category": "tax",
        "value_text": "0.21",
        "value_type": "number",
        "description": "Tasa de impuesto de respaldo legacy cuando no hay configuración de país",
    },
]


def ensure_system_defaults_table(db: Session) -> None:
    """Crea la tabla system_defaults si no existe y siembra los valores por defecto."""
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS system_defaults (
                key         VARCHAR(100) PRIMARY KEY,
                category    VARCHAR(50)  NOT NULL DEFAULT 'general',
                value_text  TEXT,
                description TEXT,
                value_type  VARCHAR(20)  NOT NULL DEFAULT 'number',
                updated_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    # Sembrar defaults sin sobreescribir valores existentes
    for row in _DEFAULTS:
        db.execute(
            text(
                """
                INSERT INTO system_defaults (key, category, value_text, description, value_type)
                VALUES (:key, :category, :value_text, :description, :value_type)
                ON CONFLICT (key) DO NOTHING
                """
            ),
            row,
        )
    try:
        db.commit()
    except Exception:
        db.rollback()


def get_system_default(db: Session, key: str, default: float) -> float:
    """Obtiene un valor numérico de system_defaults, devuelve el default si no existe."""
    try:
        ensure_system_defaults_table(db)
        row = db.execute(
            text("SELECT value_text FROM system_defaults WHERE key = :key"),
            {"key": key},
        ).fetchone()
        if row and row[0] is not None:
            return float(row[0])
    except Exception as exc:
        logger.warning("system_defaults: no se pudo leer '%s': %s", key, exc)
    return default


def list_system_defaults(db: Session) -> list[dict[str, Any]]:
    """Devuelve todos los parámetros globales del sistema."""
    ensure_system_defaults_table(db)
    rows = db.execute(
        text(
            "SELECT key, category, value_text, description, value_type, updated_at "
            "FROM system_defaults ORDER BY category, key"
        )
    ).mappings().all()
    return [dict(r) for r in rows]


def update_system_default(db: Session, key: str, value: str) -> dict[str, Any] | None:
    """Actualiza el valor de un parámetro. Devuelve la fila actualizada o None si no existe."""
    ensure_system_defaults_table(db)
    result = db.execute(
        text(
            """
            UPDATE system_defaults
            SET value_text = :value, updated_at = CURRENT_TIMESTAMP
            WHERE key = :key
            RETURNING key, category, value_text, description, value_type, updated_at
            """
        ),
        {"key": key, "value": value},
    ).mappings().first()
    db.commit()
    return dict(result) if result else None
