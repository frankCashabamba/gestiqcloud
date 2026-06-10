"""
Centralized document numbering compatibility service.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

DocumentType = Literal["invoice", "sales_order", "pos_receipt", "delivery", "purchase_order"]


def generar_numero_documento(
    db: Session,
    tenant_id: str | UUID,
    tipo: DocumentType,
    serie: str = "A",
    usar_uuid: bool = False,
) -> str:
    if usar_uuid:
        import uuid

        return str(uuid.uuid4())

    tenant_uuid = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    savepoint = None
    try:
        savepoint = db.begin_nested()
        year = datetime.now(UTC).year
        num = db.execute(
            text("SELECT public.assign_next_number(CAST(:tenant AS uuid), :tipo, :anio, :serie)"),
            {
                "tenant": tenant_uuid,
                "tipo": tipo,
                "anio": int(year),
                "serie": serie,
            },
        ).scalar()
        savepoint.commit()

        if num:
            return formatear_numero(tipo, serie, year, num)
    except Exception:
        try:
            if savepoint is not None:
                savepoint.rollback()
            else:
                db.rollback()
        except Exception:
            pass

    return generar_numero_fallback(db, tenant_uuid, tipo, serie)


def formatear_numero(tipo: DocumentType, serie: str, year: int, numero: int) -> str:
    prefijos = {
        "invoice": serie,
        "sales_order": "SO",
        "pos_receipt": "POS",
        "delivery": "DEL",
        "purchase_order": "PO",
    }
    prefijo = prefijos.get(tipo, serie)
    return f"{prefijo}-{year}-{numero:06d}"


def generar_numero_fallback(
    db: Session, tenant_id: str, tipo: DocumentType, serie: str = "A"
) -> str:
    tablas = {
        "invoice": "invoices",
        "sales_order": "sales_orders",
        "pos_receipt": "pos_receipts",
        "delivery": "deliveries",
        "purchase_order": "purchases",
    }
    columnas_numero = {
        "invoice": "number",
        "sales_order": "number",
        "pos_receipt": "number",
        "purchase_order": "number",
    }

    tabla = tablas.get(tipo)
    if not tabla:
        raise ValueError(f"Tipo de documento desconocido: {tipo}")
    columna_numero = columnas_numero.get(tipo, "numero")

    year = datetime.now(UTC).year

    try:
        result = db.execute(
            text(
                f"""
                SELECT {columna_numero} FROM {tabla}
                WHERE tenant_id = :tid
                AND {columna_numero} LIKE :pattern
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ),
            {"tid": tenant_id, "pattern": f"%-{year}-%"},
        ).scalar()

        if result:
            partes = str(result).split("-")
            nuevo_num = int(partes[-1]) + 1 if len(partes) >= 3 else 1
        else:
            nuevo_num = 1
    except Exception:
        nuevo_num = 1

    return formatear_numero(tipo, serie, year, nuevo_num)


def validar_numero_unico(
    db: Session, numero: str, tipo: DocumentType, tenant_id: str | UUID
) -> bool:
    tablas = {
        "invoice": "invoices",
        "sales_order": "sales_orders",
        "pos_receipt": "pos_receipts",
        "delivery": "deliveries",
        "purchase_order": "purchases",
    }
    columnas_numero = {
        "invoice": "number",
        "sales_order": "number",
        "pos_receipt": "number",
        "purchase_order": "number",
    }

    tabla = tablas.get(tipo)
    if not tabla:
        return False
    columna_numero = columnas_numero.get(tipo, "numero")

    tenant_uuid = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id

    try:
        existe = db.execute(
            text(
                f"""
                SELECT EXISTS(
                    SELECT 1 FROM {tabla}
                    WHERE {columna_numero} = :numero
                    AND tenant_id = :tid
                )
                """
            ),
            {"numero": numero, "tid": tenant_uuid},
        ).scalar()
        return not existe
    except Exception:
        return False
