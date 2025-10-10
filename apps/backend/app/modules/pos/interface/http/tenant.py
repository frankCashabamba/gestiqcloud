from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls


router = APIRouter(
    prefix="/pos",
    tags=["POS"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


def _tid(request: Request) -> str:
    claims = getattr(request.state, "access_claims", {}) or {}
    v = claims.get("tenant_id") if isinstance(claims, dict) else None
    return str(v) if v is not None else None


class RegisterIn(BaseModel):
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    default_warehouse_id: Optional[int] = None
    metadata: Optional[dict] = None


@router.post("/registers", response_model=dict, status_code=201)
def create_register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)):
    tid = _tid(request)
    row = db.execute(
        text(
            "INSERT INTO pos_registers(tenant_id, code, name, default_warehouse_id, metadata) "
            "VALUES (current_setting('app.tenant_id', true)::uuid, :code, :name, :wh, :md) RETURNING id"
        ),
        {"code": payload.code, "name": payload.name, "wh": payload.default_warehouse_id, "md": payload.metadata},
    ).first()
    db.commit()
    return {"id": int(row[0])}


class OpenShiftIn(BaseModel):
    register_id: int
    opening_cash: float = 0


@router.post("/open_shift", response_model=dict)
def open_shift(payload: OpenShiftIn, request: Request, db: Session = Depends(get_db)):
    row = db.execute(
        text(
            "INSERT INTO pos_shifts(tenant_id, register_id, opening_cash, status) "
            "VALUES (current_setting('app.tenant_id', true)::uuid, :rid, :cash, 'open') RETURNING id"
        ),
        {"rid": payload.register_id, "cash": payload.opening_cash},
    ).first()
    db.commit()
    return {"id": int(row[0])}


class ReceiptCreateIn(BaseModel):
    shift_id: int


@router.post("/receipts", response_model=dict, status_code=201)
def create_receipt(payload: ReceiptCreateIn, request: Request, db: Session = Depends(get_db)):
    row = db.execute(
        text(
            "INSERT INTO pos_receipts(tenant_id, shift_id, status) "
            "VALUES (current_setting('app.tenant_id', true)::uuid, :sid, 'draft') RETURNING id"
        ),
        {"sid": payload.shift_id},
    ).first()
    db.commit()
    return {"id": str(row[0])}


class ItemIn(BaseModel):
    product_id: int
    qty: float = Field(gt=0)
    unit_price: float = 0
    tax: Optional[float] = None


@router.post("/receipts/{receipt_id}/add_item", response_model=dict)
def add_item(receipt_id: str, payload: ItemIn, request: Request, db: Session = Depends(get_db)):
    rec = db.execute(text("SELECT status FROM pos_receipts WHERE id=:id::uuid"), {"id": receipt_id}).first()
    if not rec or rec[0] != "draft":
        raise HTTPException(status_code=400, detail="receipt_not_draft")
    row = db.execute(
        text(
            "INSERT INTO pos_items(tenant_id, receipt_id, product_id, qty, unit_price, tax) "
            "VALUES (current_setting('app.tenant_id', true)::uuid, :rid::uuid, :pid, :q, :p, :t) RETURNING id"
        ),
        {"rid": receipt_id, "pid": payload.product_id, "q": payload.qty, "p": payload.unit_price, "t": payload.tax},
    ).first()
    db.commit()
    return {"id": int(row[0])}


class RemoveItemIn(BaseModel):
    item_id: int


@router.post("/receipts/{receipt_id}/remove_item", response_model=dict)
def remove_item(receipt_id: str, payload: RemoveItemIn, request: Request, db: Session = Depends(get_db)):
    rec = db.execute(text("SELECT status FROM pos_receipts WHERE id=:id::uuid"), {"id": receipt_id}).first()
    if not rec or rec[0] != "draft":
        raise HTTPException(status_code=400, detail="receipt_not_draft")
    db.execute(text("DELETE FROM pos_items WHERE id=:id AND receipt_id=:rid::uuid"), {"id": payload.item_id, "rid": receipt_id})
    db.commit()
    return {"ok": True}


class PaymentIn(BaseModel):
    method: str
    amount: float = Field(gt=0)
    bank_transaction_id: Optional[int] = None


@router.post("/receipts/{receipt_id}/take_payment", response_model=dict)
def take_payment(receipt_id: str, payload: PaymentIn, request: Request, db: Session = Depends(get_db)):
    rec = db.execute(text("SELECT status FROM pos_receipts WHERE id=:id::uuid"), {"id": receipt_id}).first()
    if not rec or rec[0] != "draft":
        raise HTTPException(status_code=400, detail="receipt_not_draft")
    db.execute(
        text(
            "INSERT INTO pos_payments(tenant_id, receipt_id, method, amount, bank_transaction_id) "
            "VALUES (current_setting('app.tenant_id', true)::uuid, :rid::uuid, :m, :a, :btid)"
        ),
        {"rid": receipt_id, "m": payload.method, "a": payload.amount, "btid": payload.bank_transaction_id},
    )
    db.commit()
    return {"ok": True}


class PostReceiptIn(BaseModel):
    warehouse_id: Optional[int] = None


@router.post("/receipts/{receipt_id}/post", response_model=dict)
def post_receipt(receipt_id: str, payload: PostReceiptIn, request: Request, db: Session = Depends(get_db)):
    # Ensure draft
    rec = db.execute(text("SELECT shift_id, status FROM pos_receipts WHERE id=:id::uuid"), {"id": receipt_id}).first()
    if not rec or rec[1] != "draft":
        raise HTTPException(status_code=400, detail="receipt_not_draft")
    shift_id = int(rec[0])

    # Fetch register default warehouse if not passed
    wh_id = payload.warehouse_id
    if wh_id is None:
        row = db.execute(
            text(
                "SELECT r.default_warehouse_id FROM pos_shifts s JOIN pos_registers r ON r.id=s.register_id WHERE s.id=:sid"
            ),
            {"sid": shift_id},
        ).first()
        wh_id = int(row[0]) if row and row[0] is not None else None
    if wh_id is None:
        raise HTTPException(status_code=400, detail="warehouse_required")

    # Sum items and payments
    tot_row = db.execute(
        text(
            "SELECT COALESCE(sum(qty*unit_price),0) AS subtotal, COALESCE(sum(COALESCE(tax,0)),0) AS tax FROM pos_items WHERE receipt_id=:rid::uuid"
        ),
        {"rid": receipt_id},
    ).first()
    pay_row = db.execute(
        text("SELECT COALESCE(sum(amount),0) FROM pos_payments WHERE receipt_id=:rid::uuid"),
        {"rid": receipt_id},
    ).first()
    subtotal = float(tot_row[0] or 0)
    tax = float(tot_row[1] or 0)
    total = subtotal + tax
    paid = float(pay_row[0] or 0)
    if paid + 1e-6 < total:
        raise HTTPException(status_code=400, detail="insufficient_payment")

    # Consume stock per item
    items = db.execute(
        text("SELECT product_id, qty FROM pos_items WHERE receipt_id=:rid::uuid"), {"rid": receipt_id}
    ).fetchall()
    for it in items:
        db.execute(
            text(
                "INSERT INTO stock_moves(tenant_id, product_id, warehouse_id, qty, kind, tentative, posted, ref_type, ref_id) "
                "VALUES (current_setting('app.tenant_id', true)::uuid, :pid, :wid, :q, 'issue', false, true, 'pos_receipt', :rid)"
            ),
            {"pid": int(it[0]), "wid": int(wh_id), "q": float(it[1]), "rid": receipt_id},
        )
        # update stock_items
        row = db.execute(
            text(
                "SELECT id, qty FROM stock_items WHERE warehouse_id=:wid AND product_id=:pid FOR UPDATE"
            ),
            {"wid": int(wh_id), "pid": int(it[0])},
        ).first()
        if row is None:
            db.execute(
                text(
                    "INSERT INTO stock_items(tenant_id, warehouse_id, product_id, qty) VALUES (current_setting('app.tenant_id', true)::uuid, :wid, :pid, 0)"
                ),
                {"wid": int(wh_id), "pid": int(it[0])},
            )
            cur_qty = 0.0
        else:
            cur_qty = float(row[1] or 0)
        new_qty = cur_qty - float(it[1])
        db.execute(
            text("UPDATE stock_items SET qty=:q WHERE warehouse_id=:wid AND product_id=:pid"),
            {"q": new_qty, "wid": int(wh_id), "pid": int(it[0])},
        )

    # Update receipt totals and status
    db.execute(
        text("UPDATE pos_receipts SET status='posted', totals=:tot WHERE id=:rid::uuid"),
        {"rid": receipt_id, "tot": {"subtotal": subtotal, "tax": tax, "total": total}},
    )
    db.commit()
    return {"id": receipt_id, "status": "posted", "total": total}


class CloseShiftIn(BaseModel):
    closing_cash: float


@router.post("/shifts/{shift_id}/close", response_model=dict)
def close_shift(shift_id: int, payload: CloseShiftIn, request: Request, db: Session = Depends(get_db)):
    # Compute expected cash (sum of cash payments in receipts under shift)
    cash_row = db.execute(
        text(
            "SELECT COALESCE(sum(pp.amount),0) FROM pos_payments pp JOIN pos_receipts pr ON pr.id=pp.receipt_id WHERE pr.shift_id=:sid AND pp.method='cash'"
        ),
        {"sid": shift_id},
    ).first()
    expected_cash = float(cash_row[0] or 0)
    db.execute(
        text(
            "UPDATE pos_shifts SET status='closed', closed_at=now(), closing_cash=:cc WHERE id=:sid"
        ),
        {"sid": shift_id, "cc": payload.closing_cash},
    )
    db.commit()
    return {"status": "closed", "expected_cash": expected_cash, "counted_cash": payload.closing_cash, "diff": payload.closing_cash - expected_cash}


# ------------------------------
# Queries: list + summaries
# ------------------------------

class ListQuery(BaseModel):
    status: Optional[str] = None
    since: Optional[str] = Field(default=None, description="ISO date or datetime")
    until: Optional[str] = Field(default=None, description="ISO date or datetime")
    shift_id: Optional[int] = None


@router.get("/shifts", response_model=list[dict])
def list_shifts(status: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None, db: Session = Depends(get_db)):
    sql = [
        "SELECT id, register_id, opened_at, closed_at, opening_cash, closing_cash, status FROM pos_shifts WHERE 1=1"
    ]
    params: dict = {}
    if status:
        sql.append("AND status = :st")
        params["st"] = status
    if since:
        sql.append("AND opened_at >= :since")
        params["since"] = since
    if until:
        sql.append("AND opened_at <= :until")
        params["until"] = until
    sql.append("ORDER BY opened_at DESC LIMIT 200")
    rows = db.execute(text(" ".join(sql)), params).mappings().all()
    return [dict(r) for r in rows]


@router.get("/receipts", response_model=list[dict])
def list_receipts(status: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None, shift_id: Optional[int] = None, db: Session = Depends(get_db)):
    sql = [
        "SELECT id::text AS id, shift_id, status, created_at, totals FROM pos_receipts WHERE 1=1"
    ]
    params: dict = {}
    if status:
        sql.append("AND status = :st")
        params["st"] = status
    if shift_id is not None:
        sql.append("AND shift_id = :sid")
        params["sid"] = shift_id
    if since:
        sql.append("AND created_at >= :since")
        params["since"] = since
    if until:
        sql.append("AND created_at <= :until")
        params["until"] = until
    sql.append("ORDER BY created_at DESC LIMIT 500")
    rows = db.execute(text(" ".join(sql)), params).mappings().all()
    return [dict(r) for r in rows]


@router.get("/shifts/{shift_id}/summary", response_model=dict)
def shift_summary(shift_id: int, db: Session = Depends(get_db)):
    # Totals per payment method
    pay = db.execute(
        text(
            "SELECT pp.method, COALESCE(sum(pp.amount),0) AS amount FROM pos_payments pp JOIN pos_receipts pr ON pr.id=pp.receipt_id WHERE pr.shift_id=:sid GROUP BY 1 ORDER BY 2 DESC"
        ),
        {"sid": shift_id},
    ).fetchall()
    payments = [{"method": r[0], "amount": float(r[1] or 0)} for r in pay]

    # Receipts totals
    recs = db.execute(
        text(
            "SELECT count(*) FILTER (WHERE status='posted') AS posted, count(*) FILTER (WHERE status='draft') AS draft FROM pos_receipts WHERE shift_id=:sid"
        ),
        {"sid": shift_id},
    ).first()
    posted = int(recs[0] or 0)
    draft = int(recs[1] or 0)

    # Sum totals from posted receipts
    tot = db.execute(
        text(
            "SELECT COALESCE(sum((totals->>'subtotal')::numeric),0) AS subtotal, COALESCE(sum((totals->>'tax')::numeric),0) AS tax, COALESCE(sum((totals->>'total')::numeric),0) AS total FROM pos_receipts WHERE shift_id=:sid AND status='posted'"
        ),
        {"sid": shift_id},
    ).first()
    subtotal = float(tot[0] or 0)
    tax = float(tot[1] or 0)
    total = float(tot[2] or 0)

    return {
        "shift_id": shift_id,
        "receipts": {"posted": posted, "draft": draft},
        "payments": payments,
        "totals": {"subtotal": subtotal, "tax": tax, "total": total},
    }
