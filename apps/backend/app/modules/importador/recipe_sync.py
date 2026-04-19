"""Sync importador costing documents into production recipes."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.importador import ImpDocumento
from app.modules.production.internal_api import upsert_recipe_from_import as _upsert_recipe_impl

# Public constants kept for backward compatibility with callers that import them.
RECIPE_NAME_KEYS = (
    "nombre_de_la_receta",
    "nombre_receta",
    "nombre de la receta",
    "nombre",
)

YIELD_KEYS = (
    "n_de_porciones",
    "n\u00b0_de_porciones",
    "porciones",
    "yield",
    "rendimiento",
)

WASTE_KEYS = (
    "merma",
    "merma_(recomendado_10%)",
)


def get_available_recipe_sheets(doc_data: dict) -> list[str]:
    """Return list of sheet names available in a parsed document."""
    if not isinstance(doc_data, dict):
        return []

    rows_by_sheet = doc_data.get("filas_por_hoja") or {}
    if isinstance(rows_by_sheet, dict) and rows_by_sheet:
        return [str(sheet) for sheet in rows_by_sheet.keys() if str(sheet).strip()]

    # Fallback: detect distinct sheets from _sheet field in filas
    filas = doc_data.get("filas") or []
    if isinstance(filas, list):
        seen: list[str] = []
        seen_set: set[str] = set()
        for row in filas:
            if isinstance(row, dict):
                sname = str(row.get("_sheet") or "").strip()
                if sname and sname not in seen_set:
                    seen_set.add(sname)
                    seen.append(sname)
        if seen:
            return seen

    sheets = doc_data.get("hojas") or []
    if isinstance(sheets, list):
        return [str(sheet) for sheet in sheets if str(sheet).strip()]

    active_sheet = doc_data.get("sheet_usada")
    if active_sheet:
        return [str(active_sheet)]
    return []


def upsert_recipe_from_import(
    doc: ImpDocumento, db: Session, *, sheet_override: str | None = None
) -> tuple[UUID | None, bool]:
    """Create or update one production recipe from one import sheet.

    Delegates to production.internal_api so that this module no longer owns
    Recipe / RecipeIngredient / Product model access.
    """
    return _upsert_recipe_impl(doc, db, sheet_override=sheet_override)
