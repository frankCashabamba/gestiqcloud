from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.accounting.chart_of_accounts import ChartOfAccounts
from app.models.accounting.pos_settings import PaymentMethod
from app.models.ai.incident import Incident
from app.models.core.audit_event import AuditEvent
from app.models.core.products import Product
from app.models.expenses.expense import Expense
from app.models.importador import ImpDocumento, ImpStagingLine
from app.models.inventory.stock import StockItem, StockMove
from app.models.inventory.warehouse import Warehouse
from app.models.purchases.purchase import PurchaseLine
from app.modules.importador.router import (
    SaveDocumentLineMatch,
    SaveDocumentRequest,
    SaveDocumentResponse,
    _save_document_to_expense,
    _save_document_to_purchase,
    save_document,
)
from app.modules.importador.services.product_matching import _build_document_line_matches


def _fake_request(tenant_id) -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(
            tenant_id=tenant_id,
            access_claims={"tenant_id": str(tenant_id), "user_id": str(uuid4()), "is_company_admin": True},
        )
    )


def test_save_document_to_purchase_updates_weight_stock_from_packaging_match(
    db: Session, tenant_minimal
):
    tenant_id = tenant_minimal["tenant_id"]
    if db.get_bind().dialect.name == "sqlite":
        db.execute(text("PRAGMA foreign_keys=OFF"))
    warehouse = Warehouse(tenant_id=tenant_id, code="ALM-1", name="Principal", is_active=True)
    product = Product(
        tenant_id=tenant_id,
        sku="HAR-001",
        name="Harina Tradicion Premium",
        active=True,
        stock=0,
        unit="kg",
    )
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-harina.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        fecha_documento="2026-03-19",
        monto_total=2145.0,
        datos_confirmados={
            "numero_factura": "FAC-001",
            "line_items": [
                {
                    "description": "HARINA TRADICION PREMIUM 50 KG",
                    "quantity": 50,
                    "unit_price": 42.90,
                    "total_price": 2145.0,
                }
            ],
        },
    )
    db.add_all([warehouse, product, document])
    db.flush()

    result = _save_document_to_purchase(
        db=db,
        tenant_id=tenant_id,
        user_id=str(uuid4()),
        doc=document,
        update_stock=True,
    )
    db.flush()
    db.refresh(product)

    stock_item = (
        db.query(StockItem)
        .filter(
            StockItem.tenant_id == str(tenant_id),
            StockItem.warehouse_id == str(warehouse.id),
            StockItem.product_id == str(product.id),
        )
        .first()
    )
    stock_move = (
        db.query(StockMove)
        .filter(
            StockMove.ref_type == "purchase",
            StockMove.product_id == str(product.id),
        )
        .first()
    )

    assert result["lines_matched"] == 1
    assert product.stock == pytest.approx(2500.0)
    assert stock_item is not None
    assert float(stock_item.qty) == pytest.approx(2500.0)
    assert stock_move is not None
    assert float(stock_move.qty) == pytest.approx(2500.0)


def test_save_document_to_purchase_uses_manual_line_match_and_persists_alias(
    db: Session, tenant_minimal
):
    tenant_id = tenant_minimal["tenant_id"]
    if db.get_bind().dialect.name == "sqlite":
        db.execute(text("PRAGMA foreign_keys=OFF"))
    warehouse = Warehouse(tenant_id=tenant_id, code="ALM-1", name="Principal", is_active=True)
    product = Product(
        tenant_id=tenant_id,
        sku="HAR-002",
        name="Harina Base",
        active=True,
        stock=0,
        unit="kg",
        import_aliases=None,
    )
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-manual.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        fecha_documento="2026-03-19",
        monto_total=85.8,
        datos_confirmados={
            "numero_factura": "FAC-003",
            "line_items": [
                {
                    "description": "MOLINO EXTRA SUPER 50 KG",
                    "quantity": 2,
                    "unit_price": 42.90,
                    "total_price": 85.8,
                }
            ],
        },
    )
    db.add_all([warehouse, product, document])
    db.flush()

    result = _save_document_to_purchase(
        db=db,
        tenant_id=tenant_id,
        user_id=str(uuid4()),
        doc=document,
        update_stock=True,
        line_matches=[
            SaveDocumentLineMatch(line_index=0, product_id=product.id, persist_alias=True)
        ],
    )
    db.flush()
    db.refresh(product)

    assert result["lines_matched"] == 1
    assert product.stock == pytest.approx(100.0)
    assert isinstance(product.import_aliases, list)
    assert product.import_aliases
    assert product.import_aliases[0]["name"] == "MOLINO EXTRA SUPER 50 KG"
    assert float(product.import_aliases[0]["factor"]) == pytest.approx(50.0)


def test_save_document_to_purchase_creates_new_product_from_line_match_without_raw_material_flag(
    db: Session, tenant_minimal
):
    tenant_id = tenant_minimal["tenant_id"]
    if db.get_bind().dialect.name == "sqlite":
        db.execute(text("PRAGMA foreign_keys=OFF"))
    warehouse = Warehouse(tenant_id=tenant_id, code="ALM-1", name="Principal", is_active=True)
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-producto-nuevo.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        fecha_documento="2026-03-19",
        monto_total=24.0,
        datos_confirmados={
            "numero_factura": "FAC-004",
            "line_items": [
                {
                    "description": "Caja organizadora plastica mediana",
                    "supplier_ref": "REF-HG-2210",
                    "quantity": 5,
                    "unit_price": 4.8,
                    "total_price": 24.0,
                }
            ],
        },
    )
    db.add_all([warehouse, document])
    db.flush()

    result = _save_document_to_purchase(
        db=db,
        tenant_id=tenant_id,
        user_id=str(uuid4()),
        doc=document,
        update_stock=True,
        line_matches=[SaveDocumentLineMatch(line_index=0, product_id=None, create_new=True)],
    )
    db.flush()

    product = (
        db.query(Product)
        .filter(
            Product.tenant_id == tenant_id,
            Product.name == "Caja organizadora plastica mediana",
        )
        .one()
    )
    stock_item = (
        db.query(StockItem)
        .filter(
            StockItem.tenant_id == str(tenant_id),
            StockItem.warehouse_id == str(warehouse.id),
            StockItem.product_id == str(product.id),
        )
        .one()
    )
    purchase_line = (
        db.query(PurchaseLine).filter(PurchaseLine.purchase_id == result["purchase_id"]).one()
    )

    assert result["lines_created"] == 1
    assert result["lines_matched"] == 1
    assert product.is_raw_material is False
    assert product.sku is not None
    assert product.sku.startswith("PRO-")
    assert product.category_id is None
    assert product.price == pytest.approx(4.8)
    assert product.stock == pytest.approx(5.0)
    assert product.cost_price == pytest.approx(4.8)
    assert product.product_metadata is not None
    assert product.product_metadata["import_source"] == "supplier_invoice_line_create_new"
    assert product.product_metadata["source_supplier_ref"] == "REF-HG-2210"
    assert "REF-HG-2210" in product.product_metadata["supplier_refs"]
    assert product.import_aliases[0]["supplier_ref"] == "REF-HG-2210"
    assert float(stock_item.qty) == pytest.approx(5.0)
    assert purchase_line.product_id == product.id


def test_save_document_to_purchase_matches_existing_product_by_supplier_ref(
    db: Session, tenant_minimal
):
    tenant_id = tenant_minimal["tenant_id"]
    if db.get_bind().dialect.name == "sqlite":
        db.execute(text("PRAGMA foreign_keys=OFF"))
    warehouse = Warehouse(tenant_id=tenant_id, code="ALM-1", name="Principal", is_active=True)
    product = Product(
        tenant_id=tenant_id,
        sku="PRO-001",
        name="Articulo interno distinto",
        active=True,
        stock=0,
        unit="uds",
        product_metadata={"supplier_refs": ["REF-BZ-1042"]},
        import_aliases=[],
    )
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-bazar.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        fecha_documento="2026-03-19",
        monto_total=56.4,
        datos_confirmados={
            "numero_factura": "FAC-REF-001",
            "line_items": [
                {
                    "description": "Set de tazas de ceramica 350 ml",
                    "supplier_ref": "REF-BZ-1042",
                    "quantity": 24,
                    "unit_price": 2.35,
                    "total_price": 56.4,
                }
            ],
        },
    )
    db.add_all([warehouse, product, document])
    db.flush()

    result = _save_document_to_purchase(
        db=db,
        tenant_id=tenant_id,
        user_id=str(uuid4()),
        doc=document,
        update_stock=True,
    )
    db.flush()
    db.refresh(product)

    assert result["lines_matched"] == 1
    assert product.stock == pytest.approx(24.0)
    assert isinstance(product.import_aliases, list)
    assert product.import_aliases[0]["supplier_ref"] == "REF-BZ-1042"


def test_build_document_line_matches_does_not_autoselect_trivial_partial_match(
    db: Session, tenant_minimal
):
    tenant_id = tenant_minimal["tenant_id"]
    product = Product(
        tenant_id=tenant_id,
        name="木片形状  5/包\n椭圆",
        active=True,
        stock=0,
        unit="uds",
    )
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-bazar.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        datos_confirmados={
            "line_items": [
                {
                    "description": "Velas LED decorativas",
                    "quantity": 20,
                    "unit_price": 3.1,
                    "total_price": 62.0,
                }
            ],
        },
    )
    db.add_all([product, document])
    db.flush()

    lines = _build_document_line_matches(db, tenant_id, document)

    assert len(lines) == 1
    assert lines[0].selected_product_id is None


def test_save_document_supplier_invoice_message_surfaces_stock_warning_when_unmatched(
    db: Session, tenant_minimal, monkeypatch
):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-sin-match.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        fecha_documento="2026-03-19",
        monto_total=2145.0,
        datos_confirmados={
            "numero_factura": "FAC-002",
            "line_items": [
                {
                    "description": "PRODUCTO SIN MATCH 50 KG",
                    "quantity": 50,
                    "unit_price": 42.90,
                    "total_price": 2145.0,
                }
            ],
        },
    )
    db.add(document)
    db.commit()

    purchase_id = uuid4()
    monkeypatch.setattr(
        "app.modules.importador.router._save_document_to_purchase",
        lambda **_kwargs: {
            "purchase_id": purchase_id,
            "status": "created",
            "lines_created": 1,
            "lines_matched": 0,
            "unmatched_descriptions": ["PRODUCTO SIN MATCH 50 KG"],
            "warehouse_id": None,
            "message": "Compra registrada. No se actualizo el stock: sin producto coincidente.",
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.router._save_document_to_expense",
        lambda **_kwargs: SaveDocumentResponse(
            target="expenses",
            destination="supplier_invoice",
            status="created",
            record_id=str(uuid4()),
            message="Documento guardado en gastos.",
        ),
    )

    result = save_document(
        document.id,
        SaveDocumentRequest(
            destination="supplier_invoice",
            update_stock=True,
            payment_status="pending",
        ),
        _fake_request(tenant_id),
        db,
    )

    assert result.target == "purchases"
    assert result.message is not None
    assert "No se actualiz" in result.message
    assert "Gasto creado (pending)." in result.message


def test_save_document_supplier_invoice_persists_incident_and_audit_warning(
    db: Session, tenant_minimal, monkeypatch
):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-warning.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        fecha_documento="2026-03-19",
        monto_total=120.0,
        datos_confirmados={
            "numero_factura": "FAC-WARN-001",
            "line_items": [
                {
                    "description": "Velas LED decorativas",
                    "quantity": 20,
                    "unit_price": 3.1,
                    "total_price": 62.0,
                }
            ],
        },
    )
    db.add(document)
    db.commit()

    purchase_id = uuid4()
    monkeypatch.setattr(
        "app.modules.importador.router._save_document_to_purchase",
        lambda **_kwargs: {
            "purchase_id": purchase_id,
            "status": "created",
            "lines_created": 1,
            "lines_matched": 0,
            "unmatched_descriptions": ["Velas LED decorativas"],
            "warehouse_id": str(uuid4()),
            "message": "Compra registrada. No se actualizo el stock: sin producto coincidente.",
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.router._save_document_to_expense",
        lambda **_kwargs: SaveDocumentResponse(
            target="expenses",
            destination="supplier_invoice",
            status="created",
            record_id=str(uuid4()),
            message="Documento guardado en gastos.",
        ),
    )

    save_document(
        document.id,
        SaveDocumentRequest(
            destination="supplier_invoice",
            update_stock=True,
            payment_status="pending",
        ),
        _fake_request(tenant_id),
        db,
    )

    incident = (
        db.query(Incident)
        .filter(
            Incident.tenant_id == tenant_id,
            Incident.type == "warning",
            Incident.auto_detected.is_(True),
        )
        .order_by(Incident.created_at.desc())
        .first()
    )
    audit = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.action == "warning",
            AuditEvent.entity_type == "importador_document",
            AuditEvent.entity_id == str(document.id),
        )
        .order_by(AuditEvent.created_at.desc())
        .first()
    )

    assert incident is not None
    assert "líneas sin stock" in incident.title.lower()
    assert incident.context is not None
    assert incident.context["document_id"] == str(document.id)
    assert incident.context["purchase_id"] == str(purchase_id)
    assert incident.context["unmatched_descriptions"] == ["Velas LED decorativas"]

    assert audit is not None
    assert audit.changes is not None
    assert audit.changes["unmatched_descriptions"] == ["Velas LED decorativas"]
    assert audit.changes["incident_id"] == str(incident.id)


def test_save_document_requires_confirmation_before_supplier_invoice_save(
    db: Session, tenant_minimal
):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-sin-confirmar.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        fecha_documento="2026-03-19",
        monto_total=2145.0,
        datos_extraidos={
            "numero_factura": "FAC-RAW-001",
            "line_items": [{"description": "HARINA", "quantity": 1, "unit_price": 10.0}],
        },
        datos_confirmados=None,
    )
    db.add(document)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        save_document(
            document.id,
            SaveDocumentRequest(destination="supplier_invoice"),
            _fake_request(tenant_id),
            db,
        )

    assert exc_info.value.status_code == 409
    assert "confirmar" in str(exc_info.value.detail).lower()


def test_save_document_marks_staging_as_imported_with_target(
    db: Session, tenant_minimal, monkeypatch
):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-staging.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        fecha_documento="2026-03-19",
        monto_total=2145.0,
        datos_confirmados={
            "numero_factura": "FAC-STG-001",
            "line_items": [{"description": "HARINA", "quantity": 1, "unit_price": 10.0}],
        },
    )
    db.add(document)
    db.flush()
    line = ImpStagingLine(
        tenant_id=tenant_id,
        documento_id=document.id,
        line_number=1,
        sheet_name="__document__",
        raw_data={"numero_factura": "FAC-STG-001"},
        estado="VALID",
    )
    db.add(line)
    db.commit()

    purchase_id = uuid4()
    monkeypatch.setattr(
        "app.modules.importador.router._save_document_to_purchase",
        lambda **_kwargs: {
            "purchase_id": purchase_id,
            "status": "created",
            "lines_created": 1,
            "lines_matched": 1,
            "unmatched_descriptions": [],
            "warehouse_id": None,
            "message": "Compra registrada.",
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.router._save_document_to_expense",
        lambda **_kwargs: SaveDocumentResponse(
            target="expenses",
            destination="supplier_invoice",
            status="created",
            record_id=str(uuid4()),
            message="Documento guardado en gastos.",
        ),
    )

    save_document(
        document.id,
        SaveDocumentRequest(destination="supplier_invoice", payment_status="pending"),
        _fake_request(tenant_id),
        db,
    )

    db.refresh(line)
    assert line.estado == "IMPORTED"
    assert line.target_table == "purchases"
    assert str(line.target_id) == str(purchase_id)
    assert line.imported_at is not None


def test_save_document_to_expense_uses_tenant_payment_method_from_table(
    db: Session, tenant_minimal
):
    tenant_id = tenant_minimal["tenant_id"]
    payment_account = ChartOfAccounts(
        tenant_id=tenant_id,
        code="1.1.1.02",
        name="Banco principal",
        type="ASSET",
        level=4,
        can_post=True,
        active=True,
        debit_balance=Decimal("0"),
        credit_balance=Decimal("0"),
        balance=Decimal("0"),
    )
    db.add(payment_account)
    db.flush()

    payment_method = PaymentMethod(
        tenant_id=tenant_id,
        name="Transferencia bancaria",
        description="Transferencia o deposito",
        account_id=payment_account.id,
        is_active=True,
    )
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-transferencia.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        fecha_documento="2026-03-19",
        monto_total=2145.0,
        datos_confirmados={
            "numero_factura": "FAC-004",
            "concepto": "Compra de harina",
        },
    )
    db.add_all([payment_method, document])
    db.commit()

    result = _save_document_to_expense(
        db=db,
        tenant_id=tenant_id,
        user_id=str(uuid4()),
        doc=document,
        body=SaveDocumentRequest(
            destination="expense",
            payment_status="paid",
            payment_method_id=payment_method.id,
        ),
    )
    db.commit()

    expense = db.query(Expense).filter(Expense.id == UUID(str(result.record_id))).first()

    assert expense is not None
    assert expense.payment_method == "Transferencia bancaria"
    assert expense.notes is not None
    assert "Metodo de pago: Transferencia bancaria" in expense.notes


def test_save_document_to_expense_falls_back_to_detected_payment_method_from_document(
    db: Session, tenant_minimal
):
    tenant_id = tenant_minimal["tenant_id"]
    payment_account = ChartOfAccounts(
        tenant_id=tenant_id,
        code="1.1.1.03",
        name="Caja principal",
        type="ASSET",
        level=4,
        can_post=True,
        active=True,
        debit_balance=Decimal("0"),
        credit_balance=Decimal("0"),
        balance=Decimal("0"),
    )
    db.add(payment_account)
    db.flush()

    payment_method = PaymentMethod(
        tenant_id=tenant_id,
        name="Transferencia bancaria",
        description="Transferencia o deposito",
        account_id=payment_account.id,
        is_active=True,
    )
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-detecta-pago.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        fecha_documento="2026-03-19",
        monto_total=2145.0,
        datos_confirmados={
            "numero_factura": "FAC-005",
            "concepto": "Compra de harina",
            "payment_method": "Forma de pago: Transferencia bancaria",
        },
    )
    db.add_all([payment_method, document])
    db.commit()

    result = _save_document_to_expense(
        db=db,
        tenant_id=tenant_id,
        user_id=str(uuid4()),
        doc=document,
        body=SaveDocumentRequest(
            destination="expense",
            payment_status="paid",
        ),
    )
    db.commit()

    expense = db.query(Expense).filter(Expense.id == UUID(str(result.record_id))).first()

    assert expense is not None
    assert expense.payment_method == "Transferencia bancaria"
