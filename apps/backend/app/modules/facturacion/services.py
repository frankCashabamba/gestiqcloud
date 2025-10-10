"""Module: services.py

Auto-generated module docstring."""

import json

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.core.facturacion import Invoice
from sqlalchemy import text
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
    """
    Genera número de factura de forma atómica usando la función SQL assign_next_number
    si está disponible; cae a un algoritmo simple si no existe la función.
    """
    try:
        # Intenta usar el tenant UUID actual desde el GUC y la función SQL
        tenant_uuid = db.execute(text("SELECT public.current_tenant()::text")).scalar()
        year = db.execute(text("SELECT EXTRACT(year FROM now())::int")).scalar()
        if tenant_uuid and year:
            num = db.execute(
                text(
                    "SELECT public.assign_next_number(:tenant::uuid, :tipo, :anio, :serie)"
                ),
                {"tenant": tenant_uuid, "tipo": "invoice", "anio": int(year), "serie": "A"},
            ).scalar()
            if num:
                return str(num)
    except Exception:
        # fallback seguro más abajo
        pass

    # Fallback no atómico (sólo útil en dev/test): buscar último y sumar 1
    ultima = (
        db.query(Invoice)
        .filter(Invoice.empresa_id == empresa_id, Invoice.estado == "emitida")
        .order_by(Invoice.id.desc())
        .first()
    )
    if ultima and isinstance(ultima.numero, str) and ultima.numero.strip():
        try:
            tail = ultima.numero.split("-")[-1]
            nuevo_num = int(tail) + 1
        except Exception:
            nuevo_num = 1
    else:
        nuevo_num = 1
    return f"A-{int(db.execute(text('SELECT EXTRACT(year FROM now())::int')).scalar())}-{nuevo_num:06d}"
