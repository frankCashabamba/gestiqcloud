"""Servicio de cola de re-procesamiento por aprendizaje.

Identifica documentos ya confirmados cuyo snapshot ha aprendido cosas nuevas
desde que fueron procesados, y los marca para revisión.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

_REPROCESS_QUEUE_SQL = """
SELECT
    d.id,
    d.nombre_archivo,
    d.tipo_documento_detectado,
    d.estado,
    d.confianza_clasificacion,
    d.recipe_snapshot_id,
    d.updated_at,
    COALESCE((s.content_json->>'learning_version')::int, 0)          AS snapshot_version,
    COALESCE((d.raw_ai_json->'run'->>'learning_version_applied')::int,
             (d.raw_ai_json->'run'->'recipe_resolution'->>'learning_version_applied')::int,
             0)                                                        AS applied_version
FROM imp_documento d
JOIN icu_recipe_snapshot s ON s.id = d.recipe_snapshot_id
WHERE d.tenant_id            = :tenant_id
  AND d.estado               IN ('CONFIRMED', 'REVIEW')
  AND d.recipe_snapshot_id   IS NOT NULL
  AND COALESCE((s.content_json->>'learning_version')::int, 0) > 0
  AND COALESCE((d.raw_ai_json->'run'->>'learning_version_applied')::int,
               (d.raw_ai_json->'run'->'recipe_resolution'->>'learning_version_applied')::int,
               0)
      < COALESCE((s.content_json->>'learning_version')::int, 0)
ORDER BY d.updated_at DESC
LIMIT :limit
"""


def list_reprocess_candidates(
    db: Session,
    *,
    tenant_id: UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Devuelve documentos cuyo snapshot aprendió cosas nuevas desde que fueron procesados."""
    rows = db.execute(
        sa_text(_REPROCESS_QUEUE_SQL),
        {"tenant_id": str(tenant_id), "limit": max(1, min(limit, 200))},
    ).fetchall()
    return [
        {
            "id": row[0],
            "nombre_archivo": row[1],
            "tipo_documento_detectado": row[2],
            "estado": row[3],
            "confianza_clasificacion": float(row[4]) if row[4] is not None else None,
            "recipe_snapshot_id": row[5],
            "updated_at": row[6],
            "snapshot_learning_version": row[7],
            "applied_learning_version": row[8],
            "version_lag": row[7] - row[8],
        }
        for row in rows
    ]


def flag_reprocess_candidates(
    db: Session,
    *,
    tenant_id: UUID,
    limit: int = 50,
) -> int:
    """Marca como requiere_revision los candidatos a re-procesamiento.

    Devuelve el número de documentos marcados.
    """
    candidates = list_reprocess_candidates(db, tenant_id=tenant_id, limit=limit)
    if not candidates:
        return 0

    ids = [str(row["id"]) for row in candidates]
    result = db.execute(
        sa_text(
            "UPDATE imp_documento "
            "SET requiere_revision = TRUE "
            "WHERE id = ANY(CAST(:ids AS uuid[])) AND requiere_revision = FALSE"
        ),
        {"ids": ids},
    )
    db.commit()
    return result.rowcount or 0
