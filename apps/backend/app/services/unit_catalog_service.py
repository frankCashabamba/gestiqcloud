"""Helpers for operational unit codes exposed to tenant/frontend flows.

The admin global catalog stores descriptive codes like ``UN``/``KG`` plus an
abbreviation. Tenant runtime flows (recipes, inventory, production) need short
operational tokens compatible with existing conversion logic.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models.core.global_catalogs import UnitOfMeasure

DEFAULT_PUBLIC_UNITS = [
    {"code": "uds", "label": "Unidad"},
    {"code": "kg", "label": "Kilogramo"},
    {"code": "g", "label": "Gramo"},
    {"code": "L", "label": "Litro"},
    {"code": "ml", "label": "Mililitro"},
    {"code": "m", "label": "Metro"},
    {"code": "m2", "label": "Metro cuadrado"},
    {"code": "m3", "label": "Metro cubico"},
    {"code": "pair", "label": "Par"},
    {"code": "set", "label": "Juego"},
    {"code": "dozen", "label": "Docena"},
]

_KNOWN_UNIT_ALIASES = {
    "-": "uds",
    "un": "uds",
    "unit": "uds",
    "units": "uds",
    "und": "uds",
    "uni": "uds",
    "unidad": "uds",
    "unidades": "uds",
    "uds": "uds",
    "ud": "uds",
    "pcs": "uds",
    "pc": "uds",
    "pieza": "uds",
    "piezas": "uds",
    "pza": "uds",
    "cantidad": "uds",
    "doc": "dozen",
    "docena": "dozen",
    "docenas": "dozen",
    "dozen": "dozen",
    "kg": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "kilogramo": "kg",
    "kilogramos": "kg",
    "g": "g",
    "gr": "g",
    "gramo": "g",
    "gramos": "g",
    "lb": "lb",
    "lbs": "lb",
    "libra": "lb",
    "libras": "lb",
    "pound": "lb",
    "pounds": "lb",
    "oz": "oz",
    "onza": "oz",
    "onzas": "oz",
    "ton": "ton",
    "tonelada": "ton",
    "toneladas": "ton",
    "mg": "mg",
    "l": "L",
    "lt": "L",
    "ltr": "L",
    "litr": "L",
    "litro": "L",
    "litros": "L",
    "ml": "ml",
    "mililitro": "ml",
    "mililitros": "ml",
    "gal": "gal",
    "galon": "gal",
    "galones": "gal",
    "qt": "qt",
    "pt": "pt",
    "cup": "cup",
    "fl_oz": "fl_oz",
    "tbsp": "tbsp",
    "tsp": "tsp",
    "pair": "pair",
    "par": "pair",
    "set": "set",
    "juego": "set",
    "m": "m",
    "metro": "m",
    "metros": "m",
    "m2": "m2",
    "m^2": "m2",
    "m²": "m2",
    "metro_cuadrado": "m2",
    "metros_cuadrados": "m2",
    "m3": "m3",
    "m^3": "m3",
    "m³": "m3",
    "metro_cubico": "m3",
    "metros_cubicos": "m3",
}


def _sanitize_unit_token(raw: str | None) -> str:
    token = str(raw or "").strip().replace("-", "_").replace(" ", "_")
    return "".join(ch for ch in token if ch.isalnum() or ch == "_")


def normalize_operational_unit(
    raw_unit: str | None,
    *,
    default: str = "uds",
    valid_units: Iterable[str] | None = None,
) -> str:
    """Normalize unit tokens to operational runtime codes.

    When ``valid_units`` is provided, the returned value prefers an exact
    existing code from that set (case-insensitive).
    """

    raw = str(raw_unit or "").strip()
    if not raw or raw == "-" or raw.isdigit():
        return default

    exact_valid = {str(code).lower(): str(code) for code in (valid_units or []) if code}
    raw_lower = raw.lower()
    if raw_lower in exact_valid:
        return exact_valid[raw_lower]

    normalized = _KNOWN_UNIT_ALIASES.get(raw_lower)
    if normalized is None:
        sanitized = _sanitize_unit_token(raw).lower()
        normalized = _KNOWN_UNIT_ALIASES.get(sanitized, sanitized or default)

    if exact_valid:
        if normalized.lower() in exact_valid:
            return exact_valid[normalized.lower()]
        for code in exact_valid.values():
            candidate = normalize_operational_unit(code, default=default)
            if candidate.lower() == normalized.lower():
                return code

    return normalized


def serialize_public_unit(unit: UnitOfMeasure) -> dict[str, str]:
    public_code = normalize_operational_unit(unit.abbreviation or unit.code)
    return {"code": public_code, "label": unit.name}


def list_public_units(db: Session) -> list[dict[str, str]]:
    rows = (
        db.query(UnitOfMeasure)
        .filter(UnitOfMeasure.active.is_(True))
        .order_by(UnitOfMeasure.code.asc())
        .all()
    )
    if not rows:
        return [dict(item) for item in DEFAULT_PUBLIC_UNITS]
    return [serialize_public_unit(row) for row in rows]
