from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls
from app.api.email.email_utils import enviar_correo_bienvenida as _send
from app.models.core.facturacion import Invoice

router = APIRouter(
    prefix="/facturacion",
    tags=["Facturacion"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


@router.post("/{factura_id}/send_email", response_model=dict)
def send_invoice_email(factura_id: int, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter_by(id=factura_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="invoice_not_found")
    # Placeholder: usa correo del cliente si existe; reutiliza util de bienvenida
    try:
        email = getattr(getattr(inv, "cliente", None), "email", None) or ""
        if not email:
            raise ValueError("missing_client_email")
        _send(email, inv.numero or "Factura", getattr(getattr(inv, "empresa", None), "nombre", ""), None)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

