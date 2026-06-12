"""Helpers for operational unit codes exposed to tenant/frontend flows.

The admin global catalog stores descriptive codes like ``UN``/``KG`` plus an
abbreviation. Tenant runtime flows (recipes, inventory, production) need short
operational tokens compatible with existing conversion logic.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import text
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


def ensure_unit_aliases_seeded(db: Session) -> None:
    """Crea la tabla unit_aliases si no existe y siembra desde _KNOWN_UNIT_ALIASES."""
    # El rol de aplicación es NO-superuser y no tiene CREATE en el esquema.
    # Solo intentamos el DDL si la tabla aún no existe (BD virgen); en dev/prod
    # ya existe vía migración, así que esto es no-op y no toca permisos.
    from app.config.database import table_exists

    if not table_exists(db, "unit_aliases"):
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS unit_aliases (
                    alias        VARCHAR(50)  PRIMARY KEY,
                    canonical    VARCHAR(20)  NOT NULL,
                    updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
    for alias, canonical in _KNOWN_UNIT_ALIASES.items():
        db.execute(
            text(
                "INSERT INTO unit_aliases (alias, canonical) VALUES (:alias, :canonical) "
                "ON CONFLICT (alias) DO NOTHING"
            ),
            {"alias": alias, "canonical": canonical},
        )
    try:
        db.commit()
    except Exception:
        db.rollback()


def load_unit_aliases(db: Session) -> dict[str, str]:
    """Carga el diccionario de aliases desde BD, con _KNOWN_UNIT_ALIASES como fallback base."""
    ensure_unit_aliases_seeded(db)
    try:
        rows = db.execute(text("SELECT alias, canonical FROM unit_aliases")).fetchall()
        if rows:
            # BD extiende/sobreescribe el dict de código
            merged = dict(_KNOWN_UNIT_ALIASES)
            for alias, canonical in rows:
                merged[str(alias).strip().lower()] = str(canonical).strip()
            return merged
    except Exception:
        pass
    return dict(_KNOWN_UNIT_ALIASES)


def _sanitize_unit_token(raw: str | None) -> str:
    token = str(raw or "").strip().replace("-", "_").replace(" ", "_")
    return "".join(ch for ch in token if ch.isalnum() or ch == "_")


def normalize_operational_unit(
    raw_unit: str | None,
    *,
    default: str = "uds",
    valid_units: Iterable[str] | None = None,
    extra_aliases: dict[str, str] | None = None,
) -> str:
    """Normalize unit tokens to operational runtime codes.

    ``extra_aliases`` permite pasar aliases cargados desde BD (via load_unit_aliases)
    que extienden/sobreescriben el dict de código. Callers sin db omiten el parámetro.

    When ``valid_units`` is provided, the returned value prefers an exact
    existing code from that set (case-insensitive).
    """
    aliases = extra_aliases if extra_aliases is not None else _KNOWN_UNIT_ALIASES

    raw = str(raw_unit or "").strip()
    if not raw or raw == "-" or raw.isdigit():
        return default

    exact_valid = {str(code).lower(): str(code) for code in (valid_units or []) if code}
    raw_lower = raw.lower()
    if raw_lower in exact_valid:
        return exact_valid[raw_lower]

    normalized = aliases.get(raw_lower)
    if normalized is None:
        sanitized = _sanitize_unit_token(raw).lower()
        normalized = aliases.get(sanitized, sanitized or default)

    if exact_valid:
        if normalized.lower() in exact_valid:
            return exact_valid[normalized.lower()]
        for code in exact_valid.values():
            candidate = normalize_operational_unit(
                code, default=default, extra_aliases=extra_aliases
            )
            if candidate.lower() == normalized.lower():
                return code

    return normalized


def normalize_operational_unit_db(
    raw_unit: str | None,
    db: Session,
    *,
    default: str = "uds",
    valid_units: Iterable[str] | None = None,
) -> str:
    """Versión DB-aware de normalize_operational_unit. Carga aliases desde BD."""
    aliases = load_unit_aliases(db)
    return normalize_operational_unit(
        raw_unit, default=default, valid_units=valid_units, extra_aliases=aliases
    )


def serialize_public_unit(
    unit: UnitOfMeasure, aliases: dict[str, str] | None = None
) -> dict[str, str]:
    public_code = normalize_operational_unit(unit.abbreviation or unit.code, extra_aliases=aliases)
    return {"code": public_code, "label": unit.name}


def ensure_default_units_seeded(db: Session) -> None:
    """Siembra DEFAULT_PUBLIC_UNITS en units_of_measure si la tabla está vacía.

    Permite que la BD sea siempre la fuente de verdad; los hardcodes de
    DEFAULT_PUBLIC_UNITS quedan como datos de bootstrap, no como fallback runtime.
    """
    count = db.query(UnitOfMeasure).count()
    if count > 0:
        return
    for item in DEFAULT_PUBLIC_UNITS:
        db.add(
            UnitOfMeasure(
                code=item["code"],
                name=item["label"],
                abbreviation=item["code"],
                active=True,
            )
        )
    try:
        db.commit()
    except Exception:
        db.rollback()


def list_public_units(db: Session) -> list[dict[str, str]]:
    ensure_default_units_seeded(db)
    aliases = load_unit_aliases(db)
    rows = (
        db.query(UnitOfMeasure)
        .filter(UnitOfMeasure.active.is_(True))
        .order_by(UnitOfMeasure.code.asc())
        .all()
    )
    return [serialize_public_unit(row, aliases=aliases) for row in rows]
