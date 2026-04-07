"""Carga aliases y definiciones de campos canónicos desde la base de datos.

Fuente de verdad única:
  - imp_field_alias   → {campo: [alias, ...]}
  - imp_canonical_field → {campo: {type, projection_column}}

Caché de 5 minutos por tabla.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger("importador.field_alias_loader")

_CACHE_TTL = 300  # segundos

_alias_cache_by_tenant: dict[str, dict[str, list[str]]] = {}
_alias_cache_ts_by_tenant: dict[str, float] = {}

_field_cache: dict[str, dict] = {}
_field_cache_ts: float = 0.0


def get_field_aliases(
    db: Any,
    *,
    tenant_id: UUID | None = None,
) -> dict[str, list[str]]:
    """Retorna {campo_canonico: [alias, ...]} desde BD, caché 5 min.

    Si la BD es inalcanzable retorna {} y registra el error.
    """
    global _alias_cache_by_tenant, _alias_cache_ts_by_tenant

    now = time.monotonic()
    cache_key = str(tenant_id) if tenant_id else "__global__"
    cached = _alias_cache_by_tenant.get(cache_key)
    cached_ts = _alias_cache_ts_by_tenant.get(cache_key, 0.0)
    if cached and (now - cached_ts) < _CACHE_TTL:
        return cached

    try:
        from sqlalchemy import text as sa_text

        rows = db.execute(
            sa_text(
                """
                SELECT canonical_field, alias
                FROM imp_field_alias
                WHERE active = TRUE
                  AND (tenant_id IS NULL OR tenant_id = :tid)
                ORDER BY priority DESC, canonical_field, alias
                """
            ),
            {"tid": str(tenant_id) if tenant_id else None},
        ).fetchall()

        result: dict[str, list[str]] = {}
        for row in rows:
            field = str(row[0] or "").strip()
            alias = str(row[1] or "").strip()
            if field and alias:
                result.setdefault(field, [])
                if alias not in result[field]:
                    result[field].append(alias)

        _alias_cache_by_tenant[cache_key] = result
        _alias_cache_ts_by_tenant[cache_key] = now
        return result

    except Exception as exc:
        logger.error("No se pudieron cargar field aliases desde BD: %s", exc)
        return {}


def get_canonical_fields(
    db: Any,
    *,
    tenant_id: UUID | None = None,
) -> dict[str, dict]:
    """Retorna {campo: {type: str, projection_column: str|None}} desde BD, caché 5 min.

    type puede ser: text | numeric | date | payment_method | list
    projection_column: columna de ImpDocumento donde proyectar, o None.
    Si la BD es inalcanzable retorna {} y registra el error.
    """
    global _field_cache, _field_cache_ts

    now = time.monotonic()
    if _field_cache and (now - _field_cache_ts) < _CACHE_TTL:
        return _field_cache

    try:
        from sqlalchemy import text as sa_text

        rows = db.execute(
            sa_text(
                """
                SELECT name, field_type, projection_column, line_item_slot, label
                FROM imp_canonical_field
                WHERE active = TRUE
                ORDER BY sort_order DESC, name
                """
            )
        ).fetchall()

        result: dict[str, dict] = {}
        for row in rows:
            name = str(row[0] or "").strip()
            if name:
                result[name] = {
                    "type": str(row[1] or "text").strip(),
                    "projection_column": str(row[2]).strip() if row[2] else None,
                    "line_item_slot": str(row[3]).strip() if row[3] else None,
                    "label": str(row[4]).strip() if row[4] else None,
                }

        _field_cache = result
        _field_cache_ts = now
        return result

    except Exception as exc:
        logger.error("No se pudieron cargar canonical fields desde BD: %s", exc)
        return {}


def get_aliases_for_field(
    db: Any,
    field: str,
    *,
    tenant_id: UUID | None = None,
) -> list[str]:
    """Retorna la lista de aliases para un campo canónico específico."""
    return get_field_aliases(db, tenant_id=tenant_id).get(field, [])


def invalidate_cache() -> None:
    """Fuerza recarga desde BD en la próxima llamada."""
    global _alias_cache_by_tenant, _alias_cache_ts_by_tenant, _field_cache_ts
    _alias_cache_by_tenant = {}
    _alias_cache_ts_by_tenant = {}
    _field_cache_ts = 0.0
