"""Unit tests for DocumentConverter.quote_to_sales_order."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.quotes import Quote, QuoteStatus
from app.models.sales.order import SalesOrder, SalesOrderItem
from app.models.tenant import Tenant
from app.modules.shared.services.document_converter import DocumentConverter


def _ensure_tables(db: Session) -> None:
    bind = db.get_bind()
    Tenant.__table__.create(bind=bind, checkfirst=True)
    Quote.__table__.create(bind=bind, checkfirst=True)
    SalesOrder.__table__.create(bind=bind, checkfirst=True)
    SalesOrderItem.__table__.create(bind=bind, checkfirst=True)


def _make_tenant(db: Session) -> uuid.UUID:
    tid = uuid.uuid4()
    db.add(Tenant(id=tid, name=f"T-{tid.hex[:6]}", slug=f"t-{tid.hex[:8]}", base_currency="EUR"))
    db.commit()
    return tid


def _make_quote(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    status: str = QuoteStatus.APPROVED.value,
    lines: list[dict] | None = None,
) -> Quote:
    q = Quote(
        tenant_id=tenant_id,
        number=f"Q-{uuid.uuid4().hex[:8]}",
        customer_id=uuid.uuid4(),
        status=status,
        lines=[
            {
                "product_id": str(uuid.uuid4()),
                "name": "Item A",
                "qty": 2,
                "unit_price": 10.0,
                "tax_rate": 0.21,
                "discount_percent": 0,
                "line_total": 24.20,
            }
        ]
        if lines is None
        else lines,
        subtotal=20.0,
        tax=4.20,
        total=24.20,
        currency="EUR",
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def test_quote_to_sales_order_creates_order_and_marks_converted(db: Session) -> None:
    _ensure_tables(db)
    tid = _make_tenant(db)
    quote = _make_quote(db, tid)

    converter = DocumentConverter(db)
    order_id = converter.quote_to_sales_order(quote_id=quote.id, tenant_id=tid)

    assert order_id is not None
    order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    assert order is not None
    assert float(order.total) == pytest.approx(24.20)
    assert order.currency == "EUR"
    items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order_id).all()
    assert len(items) == 1
    assert float(items[0].qty) == 2
    assert float(items[0].unit_price) == 10.0

    db.refresh(quote)
    assert quote.status == QuoteStatus.CONVERTED.value
    assert quote.converted_to_order_id == order_id
    assert quote.converted_at is not None


def test_quote_to_sales_order_rejects_non_approved(db: Session) -> None:
    _ensure_tables(db)
    tid = _make_tenant(db)
    quote = _make_quote(db, tid, status=QuoteStatus.DRAFT.value)

    converter = DocumentConverter(db)
    with pytest.raises(ValueError):
        converter.quote_to_sales_order(quote_id=quote.id, tenant_id=tid)


def test_quote_to_sales_order_rejects_already_converted(db: Session) -> None:
    _ensure_tables(db)
    tid = _make_tenant(db)
    quote = _make_quote(db, tid)
    converter = DocumentConverter(db)
    converter.quote_to_sales_order(quote_id=quote.id, tenant_id=tid)

    with pytest.raises(ValueError):
        converter.quote_to_sales_order(quote_id=quote.id, tenant_id=tid)


def test_quote_to_sales_order_requires_lines(db: Session) -> None:
    _ensure_tables(db)
    tid = _make_tenant(db)
    quote = _make_quote(db, tid, lines=[])

    converter = DocumentConverter(db)
    with pytest.raises(ValueError):
        converter.quote_to_sales_order(quote_id=quote.id, tenant_id=tid)


def test_quote_to_sales_order_unknown_quote(db: Session) -> None:
    _ensure_tables(db)
    tid = _make_tenant(db)
    converter = DocumentConverter(db)
    with pytest.raises(ValueError):
        converter.quote_to_sales_order(quote_id=uuid.uuid4(), tenant_id=tid)
