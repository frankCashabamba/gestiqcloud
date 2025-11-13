from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls
from app.api.email.email_utils import enviar_correo_bienvenida as _send
from app.models.core.facturacion import Invoice
from app.models.tenant import Tenant

router = APIRouter(
    prefix="/facturacion",
    tags=["Facturacion"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


@router.post("/{factura_id}/send_email", response_model=dict)
def send_invoice_email(factura_id: str, db: Session = Depends(get_db)):
    try:
        factura_uuid = UUID(str(factura_id))
    except Exception:
        raise HTTPException(status_code=400, detail="factura_id_invalido")
    inv = db.query(Invoice).filter_by(id=factura_uuid).first()
    if not inv:
        raise HTTPException(status_code=404, detail="invoice_not_found")
    # Placeholder: usa correo del cliente si existe; reutiliza util de bienvenida
    try:
        email = getattr(getattr(inv, "cliente", None), "email", None) or ""
        if not email:
            raise ValueError("missing_client_email")
        # Get tenant name for email context (Empresa no longer exists)
        tenant = db.query(Tenant).filter(Tenant.id == inv.tenant_id).first()
        tenant_name = tenant.name if tenant else ""
        _send(email, inv.numero or "Factura", tenant_name, None)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
