"""Carga aliases de campos canónicos desde la base de datos.

Los aliases viven en imp_field_alias (tenant_id=NULL para globales).
Caché de 5 minutos. Fuente de verdad única: imp_field_alias en BD.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger("importador.field_alias_loader")

_CACHE_TTL = 300  # segundos

_cache: dict[str, list[str]] = {}
_cache_ts: float = 0.0


def get_field_aliases(
    db: Any,
    *,
    tenant_id: UUID | None = None,
) -> dict[str, list[str]]:
    """Retorna {campo_canonico: [alias, ...]} desde BD, caché 5 min.

    Si la BD es inalcanzable retorna {} y registra el error.
    La fuente de verdad son los registros en imp_field_alias.
    """
    global _cache, _cache_ts

    now = time.monotonic()
    if _cache and (now - _cache_ts) < _CACHE_TTL:
        return _cache

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

        _cache = result
        _cache_ts = now
        return result

    except Exception as exc:
        logger.error("No se pudieron cargar field aliases desde BD: %s", exc)
        return {}


def get_aliases_for_field(
    db: Any,
    field: str,
    *,
    tenant_id: UUID | None = None,
) -> list[str]:
    """Retorna la lista de aliases para un campo canónico específico."""
    aliases = get_field_aliases(db, tenant_id=tenant_id)
    return aliases.get(field, [])


def invalidate_cache() -> None:
    """Fuerza recarga desde BD en la próxima llamada."""
    global _cache_ts
    _cache_ts = 0.0
