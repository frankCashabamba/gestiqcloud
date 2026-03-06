"""
Servicio para importar hoja REGISTRO como historial diario de producción.

Flujo:
1. Leer la hoja REGISTRO del documento importado (datos_extraidos.filas_por_hoja.REGISTRO)
2. Inferir la fecha del nombre del archivo (DD-MM-YY o DD-MM-YYYY)
3. Por cada fila válida, buscar receta/producto por nombre (fuzzy case-insensitive)
4. Insertar DailyProductionLog (upsert por tenant+date+product_name)
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.production._daily_log import DailyProductionLog
from app.models.recipes import Recipe


# Columnas que aceptamos (normalizadas a minúsculas sin espacios extra)
_COL_PRODUCT = {"producto", "product", "item", "descripcion", "nombre"}
_COL_QTY_PRODUCED = {"cantidad", "quantity", "qty", "produccion", "producido", "qty_produced"}
_COL_PRICE = {"precio unitario venta", "precio", "price", "unit_price", "precio venta", "precio unitario"}
_COL_QTY_SOLD = {"venta diaria", "venta", "vendido", "qty_sold", "ventas", "sold"}


def _norm(s: Any) -> str:
    """Normaliza un valor de celda a string limpio en minúsculas."""
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _find_col(headers: list[str], candidates: set[str]) -> int | None:
    """Devuelve el índice de la primera columna cuyo nombre normalizado coincide."""
    for i, h in enumerate(headers):
        if _norm(h) in candidates:
            return i
    return None


def _parse_date_from_filename(filename: str) -> date | None:
    """
    Extrae la fecha del nombre del archivo.
    Formatos soportados: DD-MM-YY, DD-MM-YYYY (con cualquier separador . - _)
    Ejemplos: "19-01-24..xlsx", "05.03.2024.xlsx"
    """
    # Buscar patrón DD-MM-YYYY o DD-MM-YY
    m = re.search(r"(\d{1,2})[.\-_](\d{1,2})[.\-_](\d{2,4})", filename)
    if not m:
        return None
    try:
        day, month, year_raw = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year_raw < 100:
            year = 2000 + year_raw
        else:
            year = year_raw
        return date(year, month, day)
    except ValueError:
        return None


def _safe_decimal(val: Any) -> Decimal:
    try:
        return Decimal(str(val)).quantize(Decimal("0.0001"))
    except Exception:
        return Decimal("0")


def _match_recipe(db: Session, tenant_id: UUID, product_name: str) -> Recipe | None:
    """Busca receta por nombre ignorando mayúsculas/tildes básicas."""
    name_clean = _norm(product_name)
    results = db.execute(
        select(Recipe).where(Recipe.tenant_id == str(tenant_id))
    ).scalars().all()
    # Coincidencia exacta primero
    for r in results:
        if _norm(r.name) == name_clean:
            return r
    # Coincidencia por contenido (el nombre del import está dentro del nombre de la receta o viceversa)
    for r in results:
        rn = _norm(r.name)
        if name_clean and (name_clean in rn or rn in name_clean):
            return r
    return None


def parse_registro_rows(datos_extraidos: dict) -> list[dict]:
    """
    Extrae las filas útiles de datos_extraidos.
    Soporta tanto filas_por_hoja.REGISTRO como filas directas si la hoja única es REGISTRO.
    Devuelve lista de dicts con keys: product_name, qty_produced, unit_price, qty_sold
    """
    rows_raw: list[Any] = []

    # Intentar filas_por_hoja
    por_hoja = datos_extraidos.get("filas_por_hoja", {})
    for sheet_key in por_hoja:
        if "registro" in sheet_key.lower():
            raw = por_hoja[sheet_key]
            if isinstance(raw, list):
                rows_raw = raw
            break

    # Fallback: filas directas
    if not rows_raw:
        filas = datos_extraidos.get("filas", [])
        if isinstance(filas, list):
            rows_raw = filas

    if not rows_raw:
        return []

    # Primera fila no vacía como headers
    headers: list[str] = []
    data_rows: list[Any] = []
    for row in rows_raw:
        if not isinstance(row, (list, dict)):
            continue
        values = list(row.values()) if isinstance(row, dict) else list(row)
        if not headers:
            if any(v is not None for v in values):
                headers = [str(v or "") for v in values]
            continue
        data_rows.append(values)

    if not headers:
        return []

    col_product = _find_col(headers, _COL_PRODUCT)
    col_qty = _find_col(headers, _COL_QTY_PRODUCED)
    col_price = _find_col(headers, _COL_PRICE)
    col_sold = _find_col(headers, _COL_QTY_SOLD)  # opcional

    if col_product is None:
        return []

    result = []
    for row in data_rows:
        def _get(idx: int | None) -> Any:
            if idx is None or idx >= len(row):
                return None
            return row[idx]

        name = str(_get(col_product) or "").strip()
        if not name:
            continue

        qty_produced = _safe_decimal(_get(col_qty))
        unit_price = _safe_decimal(_get(col_price))

        # Solo los 3 campos obligatorios; VENTA DIARIA es opcional
        if qty_produced == 0 and unit_price == 0:
            continue

        qty_sold = _safe_decimal(_get(col_sold))  # 0 si no existe la columna

        result.append({
            "product_name": name,
            "qty_produced": qty_produced,
            "unit_price": unit_price,
            "qty_sold": qty_sold,
        })

    return result


def save_daily_log(
    db: Session,
    tenant_id: UUID,
    document_id: UUID,
    log_date: date,
    rows: list[dict],
    replace_existing: bool = True,
) -> dict:
    """
    Inserta (o reemplaza) los registros diarios de producción.
    Si replace_existing=True borra los del mismo tenant+fecha+documento antes de insertar.
    Devuelve estadísticas: inserted, matched_recipes, unmatched.
    """
    if replace_existing:
        existing = db.execute(
            select(DailyProductionLog).where(
                and_(
                    DailyProductionLog.tenant_id == str(tenant_id),
                    DailyProductionLog.log_date == log_date,
                    DailyProductionLog.source_document_id == str(document_id),
                )
            )
        ).scalars().all()
        for e in existing:
            db.delete(e)

    inserted = 0
    matched = 0
    unmatched: list[str] = []

    for row in rows:
        recipe = _match_recipe(db, tenant_id, row["product_name"])
        product_id = str(recipe.product_id) if recipe and recipe.product_id else None
        recipe_id = str(recipe.id) if recipe else None

        if recipe:
            matched += 1
        else:
            unmatched.append(row["product_name"])

        log = DailyProductionLog(
            tenant_id=str(tenant_id),
            log_date=log_date,
            product_name=row["product_name"],
            recipe_id=recipe_id,
            product_id=product_id,
            qty_produced=row["qty_produced"],
            unit_price=row["unit_price"],
            qty_sold=row["qty_sold"],
            source_document_id=str(document_id),
        )
        db.add(log)
        inserted += 1

    db.commit()
    return {
        "inserted": inserted,
        "matched_recipes": matched,
        "unmatched_products": unmatched,
        "log_date": log_date.isoformat(),
    }
