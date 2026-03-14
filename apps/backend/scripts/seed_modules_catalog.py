#!/usr/bin/env python
"""
Seed del catálogo de módulos del sistema en la tabla `modules`.

Qué hace:
  Inserta los módulos descubiertos desde module.json con ON CONFLICT (url) DO UPDATE,
  actualizando todos los campos excepto `active` (para no pisar customizaciones).

Requisito previo:
  La migración SQL debe haberse aplicado antes de ejecutar este script:
    ops/migrations/2026-03-14_001_modules_catalog_columns/up.sql

Cuándo ejecutar:
  - En deployments nuevos (tabla vacía).
  - Después de agregar módulos nuevos (module.json en el frontend).
  - Para sincronizar metadatos (descripción, icono, aliases, etc.) sin perder
    cambios manuales de admin en `active`, `name` y `category`.

Uso:
    cd apps/backend
    python scripts/seed_modules_catalog.py
    python scripts/seed_modules_catalog.py --dry-run   # solo muestra el plan
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.config.database import SessionLocal
from app.modules.settings.application.modules_catalog import _discover_modules_from_fs

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


def _ensure_url_index(db) -> None:
    """Crea el índice único en modules.url necesario para ON CONFLICT (url)."""
    try:
        db.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS modules_url_unique "
                "ON modules (url)"
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        log.warning("No se pudo crear índice único en url: %s", exc)


def _upsert_modules(db, dry_run: bool = False) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"inserted": [], "updated": [], "skipped": []}
    _ensure_url_index(db)

    for entry in _discover_modules_from_fs():
        catalog_id: str = str(entry["id"])
        deps = entry.get("dependencies") or []
        aliases_raw = list(entry.get("aliases") or [])
        if catalog_id not in aliases_raw:
            aliases_raw = [catalog_id] + aliases_raw
        countries = entry.get("countries") or ["ES", "EC"]
        sectors = entry.get("sectors")  # None = todos

        if dry_run:
            log.info("  [DRY-RUN] %s  (%s)", catalog_id, entry.get("name"))
            result["skipped"].append(catalog_id)
            continue

        params = {
            "id":              str(uuid.uuid4()),
            "name":            catalog_id,
            "description":     entry.get("description"),
            "icon":            entry.get("icon"),
            "category":        entry.get("category"),
            "url":             catalog_id,
            "initial_template": catalog_id,
            "context_type":    "none",
            "context_filters": json.dumps({"catalog_id": catalog_id}),
            "implemented":     bool(entry.get("implemented", True)),
            "required":        bool(entry.get("required", False)),
            "default_enabled": bool(entry.get("default_enabled", True)),
            "dependencies":    json.dumps(deps),
            "aliases":         json.dumps(aliases_raw),
            "countries":       json.dumps(countries),
            "sectors":         json.dumps(sectors) if sectors is not None else None,
        }

        try:
            row = db.execute(
                text(
                    """
                    INSERT INTO modules (
                        id, name, description, icon, category,
                        url, initial_template, context_type, context_filters,
                        active,
                        implemented, required, default_enabled,
                        dependencies, aliases, countries, sectors
                    ) VALUES (
                        CAST(:id AS uuid), :name, :description, :icon, :category,
                        :url, :initial_template, :context_type, CAST(:context_filters AS jsonb),
                        TRUE,
                        :implemented, :required, :default_enabled,
                        CAST(:dependencies AS jsonb), CAST(:aliases AS jsonb),
                        CAST(:countries AS jsonb),
                        CAST(:sectors AS jsonb)
                    )
                    ON CONFLICT (url) DO UPDATE SET
                        description     = EXCLUDED.description,
                        icon            = EXCLUDED.icon,
                        initial_template= EXCLUDED.initial_template,
                        context_type    = EXCLUDED.context_type,
                        context_filters = EXCLUDED.context_filters,
                        implemented     = EXCLUDED.implemented,
                        required        = EXCLUDED.required,
                        default_enabled = EXCLUDED.default_enabled,
                        dependencies    = EXCLUDED.dependencies,
                        aliases         = EXCLUDED.aliases,
                        countries       = EXCLUDED.countries,
                        sectors         = EXCLUDED.sectors
                    RETURNING (xmax = 0) AS is_insert
                    """
                ),
                params,
            ).scalar()
            db.commit()
            if row:
                result["inserted"].append(catalog_id)
            else:
                result["updated"].append(catalog_id)
        except Exception as exc:
            db.rollback()
            log.error("  ERROR en %s: %s", catalog_id, exc)

    return result


def main(dry_run: bool = False) -> None:
    db = SessionLocal()
    try:
        log.info("=== seed_modules_catalog ===")
        registry = _discover_modules_from_fs()
        log.info("-- Insertando / actualizando módulos (%d total) --", len(registry))
        stats = _upsert_modules(db, dry_run=dry_run)

        log.info("  Insertados : %d  %s", len(stats["inserted"]), stats["inserted"])
        log.info("  Actualizados: %d  %s", len(stats["updated"]),  stats["updated"])
        if stats["skipped"]:
            log.info("  Omitidos (dry-run): %d", len(stats["skipped"]))

        log.info("=== Listo ===")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed del catálogo de módulos en BD")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra qué se insertaría sin escribir nada en BD",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
