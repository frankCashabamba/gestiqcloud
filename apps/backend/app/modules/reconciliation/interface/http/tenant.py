from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls


router = APIRouter(
    prefix="/reconciliation",
    tags=["Reconciliation"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


class LinkIn(BaseModel):
    bank_transaction_id: int
    invoice_id: int
    amount: float = Field(gt=0)


@router.post("/link", response_model=dict)
def link_payment(payload: LinkIn, db: Session = Depends(get_db)):
    # Ensure bank tx exists
    tx = db.execute(text("SELECT id, importe FROM bank_transactions WHERE id=:id"), {"id": payload.bank_transaction_id}).first()
    if not tx:
        raise HTTPException(status_code=404, detail="bank_tx_not_found")
    # Ensure invoice exists and total
    inv = db.execute(text("SELECT id, total FROM facturas WHERE id=:id"), {"id": payload.invoice_id}).first()
    if not inv:
        raise HTTPException(status_code=404, detail="invoice_not_found")

    # Create payment record
    db.execute(
        text(
            "INSERT INTO payments(empresa_id, bank_tx_id, factura_id, fecha, importe_aplicado, notas) "
            "SELECT f.empresa_id, :tx, :inv, now()::date, :amt, 'reconciled' FROM facturas f WHERE f.id=:inv"
        ),
        {"tx": payload.bank_transaction_id, "inv": payload.invoice_id, "amt": payload.amount},
    )

    # Update invoice status based on sum payments
    s = db.execute(
        text(
            "SELECT COALESCE(sum(importe_aplicado),0) FROM payments WHERE factura_id=:inv"
        ),
        {"inv": payload.invoice_id},
    ).scalar()
    tot = float(inv[1] or 0)
    new_status = "pagada" if s + 1e-6 >= tot else "parcial"
    db.execute(text("UPDATE facturas SET estado=:st WHERE id=:id"), {"st": new_status, "id": payload.invoice_id})
    db.commit()
    return {"ok": True, "invoice_id": payload.invoice_id, "paid_total": float(s), "status": new_status}


class SuggestOut(BaseModel):
    bank_transaction_id: int
    invoice_id: int
    score: float
    amount: float
    days_diff: int


@router.get("/suggestions", response_model=List[SuggestOut])
def suggestions(
    db: Session = Depends(get_db),
    since: Optional[str] = Query(default=None),
    until: Optional[str] = Query(default=None),
    tolerance: float = Query(default=0.01),
):
    # Simple matching by amount with small tolerance and date proximity (+/- 7 days)
    sql = (
        """
        WITH cand AS (
          SELECT bt.id AS bank_id, bt.importe AS amt, f.id AS inv_id, f.total AS total,
                 abs(bt.importe - f.total) AS diff,
                 abs(EXTRACT(EPOCH FROM (bt.fecha::timestamp - f.fecha_emision::timestamp)))/86400.0 AS days
            FROM bank_transactions bt
            JOIN facturas f ON f.empresa_id = bt.empresa_id
           WHERE abs(bt.importe - f.total) <= :tol
             AND ( :since::date IS NULL OR bt.fecha >= :since::date )
             AND ( :until::date IS NULL OR bt.fecha <= :until::date )
        )
        SELECT bank_id, inv_id, (1.0/(1.0+diff)) + (1.0/(1.0+days)) AS score, amt, days::int
          FROM cand
         WHERE days <= 7
         ORDER BY score DESC
         LIMIT 50
        """
    )
    rows = db.execute(text(sql), {"tol": tolerance, "since": since, "until": until}).fetchall()
    return [SuggestOut(bank_transaction_id=int(r[0]), invoice_id=int(r[1]), score=float(r[2]), amount=float(r[3]), days_diff=int(r[4])) for r in rows]

