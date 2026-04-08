"""System defaults service for global runtime configuration."""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_raw_cache: dict[str, tuple[float, str | None]] = {}
_RAW_CACHE_TTL = 120.0  # segundos

_DEFAULTS: list[dict[str, Any]] = [
    {
        "key": "reports.low_stock_threshold",
        "category": "reports",
        "value_text": "10",
        "value_type": "number",
        "description": "Global low stock threshold used by inventory reports",
    },
    {
        "key": "invoicing.default_due_days",
        "category": "invoicing",
        "value_text": "30",
        "value_type": "number",
        "description": "Default due days for new invoices",
    },
    {
        "key": "tax.fallback_rate",
        "category": "tax",
        "value_text": "0.0",
        "value_type": "number",
        "description": "Fallback tax rate when country-specific config is missing. Set per country: ES=0.21, EC=0.12",
    },
    {
        "key": "sector.fallback_code",
        "category": "sector",
        "value_text": "panaderia",
        "value_type": "text",
        "description": "Sector code used as fallback when the requested sector has no field/category config in DB",
    },
    {
        "key": "pos.default_register_name",
        "category": "pos",
        "value_text": "Caja Principal",
        "value_type": "text",
        "description": "Name of the default POS register created during tenant onboarding",
    },
    {
        "key": "company.user_limit_default",
        "category": "company",
        "value_text": "10",
        "value_type": "number",
        "description": "Global user limit when a tenant has no company settings row yet",
    },
    {
        "key": "company.allow_custom_roles_default",
        "category": "company",
        "value_text": "true",
        "value_type": "boolean",
        "description": "Allow custom roles by default when a tenant has no company settings row yet",
    },
    {
        "key": "theme.colors.primary",
        "category": "theme",
        "value_text": "#2563eb",
        "value_type": "color",
        "description": "Global theme primary color",
    },
    {
        "key": "theme.colors.secondary",
        "category": "theme",
        "value_text": "#1e293b",
        "value_type": "color",
        "description": "Global theme secondary color",
    },
    {
        "key": "theme.colors.on_primary",
        "category": "theme",
        "value_text": "#ffffff",
        "value_type": "color",
        "description": "Text color over primary surfaces",
    },
    {
        "key": "theme.colors.bg",
        "category": "theme",
        "value_text": "#ffffff",
        "value_type": "color",
        "description": "Global background color",
    },
    {
        "key": "theme.colors.fg",
        "category": "theme",
        "value_text": "#0f172a",
        "value_type": "color",
        "description": "Global main text color",
    },
    {
        "key": "theme.colors.muted",
        "category": "theme",
        "value_text": "#64748b",
        "value_type": "color",
        "description": "Global secondary text color",
    },
    {
        "key": "theme.colors.success",
        "category": "theme",
        "value_text": "#10b981",
        "value_type": "color",
        "description": "Global success color",
    },
    {
        "key": "theme.colors.warning",
        "category": "theme",
        "value_text": "#f59e0b",
        "value_type": "color",
        "description": "Global warning color",
    },
    {
        "key": "theme.colors.danger",
        "category": "theme",
        "value_text": "#ef4444",
        "value_type": "color",
        "description": "Global danger color",
    },
    {
        "key": "theme.typography.font_family",
        "category": "theme",
        "value_text": "Inter, system-ui, sans-serif",
        "value_type": "text",
        "description": "Global theme font family",
    },
    {
        "key": "theme.typography.font_size_base",
        "category": "theme",
        "value_text": "16px",
        "value_type": "text",
        "description": "Global base font size",
    },
    {
        "key": "theme.radius.sm",
        "category": "theme",
        "value_text": "4px",
        "value_type": "text",
        "description": "Global small radius",
    },
    {
        "key": "theme.radius.md",
        "category": "theme",
        "value_text": "8px",
        "value_type": "text",
        "description": "Global medium radius",
    },
    {
        "key": "theme.radius.lg",
        "category": "theme",
        "value_text": "12px",
        "value_type": "text",
        "description": "Global large radius",
    },
    {
        "key": "theme.shadows.sm",
        "category": "theme",
        "value_text": "0 1px 2px rgba(0,0,0,.08)",
        "value_type": "text",
        "description": "Global small shadow",
    },
    {
        "key": "theme.shadows.md",
        "category": "theme",
        "value_text": "0 4px 12px rgba(0,0,0,.12)",
        "value_type": "text",
        "description": "Global medium shadow",
    },
    {
        "key": "modules.categories",
        "category": "modules",
        "value_text": '[{"id":"sales","name":"Sales","icon":"📈","order":1},{"id":"operations","name":"Operations","icon":"⚙️","order":2},{"id":"finance","name":"Finance","icon":"💼","order":3},{"id":"people","name":"People","icon":"👥","order":4},{"id":"settings","name":"Settings","icon":"⚙️","order":5},{"id":"integrations","name":"Integrations","icon":"🔌","order":6},{"id":"analytics","name":"Analytics","icon":"📊","order":7},{"id":"tools","name":"Tools","icon":"🧠","order":8}]',
        "value_type": "json",
        "description": "Module categories shown in the admin module catalog. Editable from admin.",
    },
    {
        "key": "sector.code_aliases",
        "category": "sector",
        "value_text": '{"bazar":"retail","todoa100":"retail","panerp":"panaderia","mecanico":"taller"}',
        "value_type": "json",
        "description": "Sector code aliases: maps legacy/alternative codes to canonical sector codes. Add entries here to create new aliases without deploying.",
    },
    {
        "key": "numbering.default_reset_policy",
        "category": "numbering",
        "value_text": "yearly",
        "value_type": "text",
        "description": "Reset policy for document series counters: 'yearly' resets each fiscal year, 'never' is sequential",
    },
    {
        "key": "numbering.default_series",
        "category": "numbering",
        "value_text": '[{"doc_type":"R","name_backoffice":"RBO","name_pos":"R001"},{"doc_type":"F","name":"F"},{"doc_type":"C","name":"C"}]',
        "value_type": "json",
        "description": "Default document series created at tenant onboarding. JSON array. Each entry needs doc_type; receipts use name_backoffice/name_pos, others use name.",
    },
    {
        "key": "app.version",
        "category": "app",
        "value_text": "0.1.0",
        "value_type": "text",
        "description": "Version del sistema mostrada en la interfaz. Cambiar desde el Panel Admin para reflejarlo en todos los tenants sin redeploy.",
    },
]


def ensure_system_defaults_table(db: Session) -> None:
    """Create the backing table and seed defaults if needed."""
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


def _get_raw_system_default(db: Session, key: str) -> str | None:
    now = time.monotonic()
    cached = _raw_cache.get(key)
    if cached and (now - cached[0]) <= _RAW_CACHE_TTL:
        return cached[1]
    ensure_system_defaults_table(db)
    row = db.execute(
        text("SELECT value_text FROM system_defaults WHERE key = :key"),
        {"key": key},
    ).fetchone()
    value = str(row[0]).strip() if row and row[0] is not None else None
    _raw_cache[key] = (now, value)
    return value


def get_system_default(db: Session, key: str, default: float) -> float:
    """Read a numeric default, falling back safely on errors."""
    try:
        raw = _get_raw_system_default(db, key)
        if raw:
            return float(raw)
    except Exception as exc:
        logger.warning("system_defaults: could not read numeric '%s': %s", key, exc)
    return default


def get_system_default_text(db: Session, key: str, default: str) -> str:
    """Read a text default, falling back safely on errors."""
    try:
        raw = _get_raw_system_default(db, key)
        if raw:
            return raw
    except Exception as exc:
        logger.warning("system_defaults: could not read text '%s': %s", key, exc)
    return default


def get_system_default_json(db: Session, key: str, default: Any) -> Any:
    """Read a JSON default (list or dict), falling back safely on errors."""
    import json

    try:
        raw = _get_raw_system_default(db, key)
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning("system_defaults: could not read json '%s': %s", key, exc)
    return default


def get_system_default_bool(db: Session, key: str, default: bool) -> bool:
    """Read a boolean default, falling back safely on errors."""
    try:
        raw = (_get_raw_system_default(db, key) or "").lower()
        if raw in {"1", "true", "yes", "si", "on"}:
            return True
        if raw in {"0", "false", "no", "off"}:
            return False
    except Exception as exc:
        logger.warning("system_defaults: could not read boolean '%s': %s", key, exc)
    return default


def list_system_defaults(db: Session) -> list[dict[str, Any]]:
    """Return all system default rows."""
    ensure_system_defaults_table(db)
    rows = (
        db.execute(
            text(
                "SELECT key, category, value_text, description, value_type, updated_at "
                "FROM system_defaults ORDER BY category, key"
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def update_system_default(db: Session, key: str, value: str) -> dict[str, Any] | None:
    """Update a single system default value."""
    ensure_system_defaults_table(db)
    result = (
        db.execute(
            text(
                """
            UPDATE system_defaults
            SET value_text = :value, updated_at = CURRENT_TIMESTAMP
            WHERE key = :key
            RETURNING key, category, value_text, description, value_type, updated_at
            """
            ),
            {"key": key, "value": value},
        )
        .mappings()
        .first()
    )
    db.commit()
    _raw_cache.pop(key, None)
    return dict(result) if result else None
