from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.modules.documents.application.orchestrator import DocumentOrchestrator
from app.modules.documents.application.repository import get_document, save_document
from app.modules.documents.application.store import store
from app.modules.documents.domain.config import TenantDocConfig
from app.modules.documents.domain.models import BuyerIn, SaleDraft, SaleItemIn, SellerInfo


def _build_sale() -> SaleDraft:
    return SaleDraft(
        tenantId="tnt_123",
        country="EC",
        posId="pos_01",
        currency="USD",
        buyer=BuyerIn(mode="CONSUMER_FINAL", idType="NONE", idNumber=None, name=None),
        items=[
            SaleItemIn(
                sku="SKU-1",
                name="Producto",
                qty=Decimal("1"),
                unitPrice=Decimal("10"),
                discount=Decimal("0"),
                taxCategory="DEFAULT",
            )
        ],
        payments=[],
        meta=None,
    )


def test_document_persistence_roundtrip(db):
    if db.get_bind().dialect.name != "postgresql":
        pytest.skip("Document persistence test requires PostgreSQL")

    cfg = TenantDocConfig(
        tax_profile={"DEFAULT": {"rate": 0, "code": "0"}},
        buyer_policy={"consumerFinalMaxTotal": 0},
        config_version=2,
        effective_from="2026-01-01",
    )
    seller = SellerInfo(
        tenantId="tnt_123",
        tradeName="Mi Tienda",
        legalName="Mi Tienda",
        taxId="0999999999001",
        address="Calle 123",
    )
    sale = _build_sale()
    doc = DocumentOrchestrator().issue(sale, cfg, seller, series="001-001", sequential="000000010")

    tenant_id = str(uuid4())
    db.execute(text("SET app.tenant_id = :tid"), {"tid": tenant_id})
    db.execute(text("SET session_replication_role = REPLICA"))
    save_document(
        db,
        tenant_id=tenant_id,
        doc=doc,
        config_version=cfg.config_version,
        effective_from=cfg.effective_from,
        country_pack_version="1.0.0",
    )
    loaded = get_document(db, doc.document.id)
    assert loaded is not None
    assert loaded.document.id == doc.document.id
    assert loaded.document.sequential == "000000010"


def test_document_store_fallback_roundtrip():
    cfg = TenantDocConfig(
        tax_profile={"DEFAULT": {"rate": 0, "code": "0"}},
        buyer_policy={"consumerFinalMaxTotal": 0},
        config_version=1,
    )
    seller = SellerInfo(
        tenantId="tnt_123",
        tradeName="Mi Tienda",
        legalName="Mi Tienda",
        taxId="0999999999001",
        address="Calle 123",
    )
    sale = _build_sale()
    doc = DocumentOrchestrator().issue(sale, cfg, seller, series="001-001", sequential="000000123")
    store.put(doc)
    loaded = store.get(doc.document.id)
    assert loaded is not None
    assert loaded.document.sequential == "000000123"
