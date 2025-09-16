"""Module: services.py

Auto-generated module docstring."""

import json

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.core.facturacion import Invoice
from app.modules.facturacion.crud import \
    factura_crud  # ✅ usar la instancia, no el módulo completo


async def procesar_archivo_factura(
    file: UploadFile,
    usuario_id: int,
    empresa_id: int,
    db: Session
):
    contenido = await file.read()
    facturas = json.loads(contenido)
    filename = file.filename or "archivo_sin_nombre"

    # ✅ Llamar al método de la instancia
    factura_crud.guardar_temporal(db, facturas, filename, usuario_id, empresa_id)

    return {"status": "archivo procesado", "cantidad": len(facturas)}


def generar_numero_factura(db: Session, empresa_id: int) -> str:
    """ Function generar_numero_factura - auto-generated docstring. """
    ultima = (
        db.query(Invoice)
        .filter(Invoice.empresa_id == empresa_id, Invoice.estado == "emitida")
        .order_by(Invoice.id.desc())
        .first()
    )

    if ultima and ultima.numero.startswith("F-"):
        try:
            ultimo_num = int(ultima.numero.split("-")[-1])
            nuevo_num = ultimo_num + 1
        except ValueError:
            nuevo_num = 1
    else:
        nuevo_num = 1

    return f"F-{nuevo_num:05d}"
