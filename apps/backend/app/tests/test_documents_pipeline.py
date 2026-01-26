from datetime import datetime, UTC
from decimal import Decimal
from pathlib import Path

from app.modules.country_packs.ecuador import EcuadorPack
from app.modules.documents.application.orchestrator import DocumentOrchestrator
from app.modules.documents.application.template_engine import TemplateEngine
from app.modules.documents.domain.config import TenantDocConfig
from app.modules.documents.domain.models import BuyerIn, SaleDraft, SaleItemIn, SellerInfo


def _build_sale(total: Decimal) -> SaleDraft:
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
                unitPrice=total,
                discount=Decimal("0"),
                taxCategory="DEFAULT",
            )
        ],
        payments=[],
        meta=None,
    )


def test_ecuador_pack_validation_consumer_final_limit():
    cfg = TenantDocConfig(
        buyer_policy={
            "consumerFinalMaxTotal": 50,
            "requireBuyerAboveAmount": True,
        }
    )
    sale = _build_sale(Decimal("100"))
    errors = EcuadorPack().validate(sale, cfg)
    assert errors
    assert errors[0].code == "buyer_required"


def test_orchestrator_issue_applies_tax_profile():
    cfg = TenantDocConfig(
        tax_profile={"DEFAULT": {"rate": 0.12, "code": "2"}},
        buyer_policy={"consumerFinalMaxTotal": 0},
    )
    sale = _build_sale(Decimal("100"))
    seller = SellerInfo(
        tenantId="tnt_123",
        tradeName="Mi Tienda",
        legalName="Mi Tienda",
        taxId="0999999999001",
        address="Calle 123",
    )
    doc = DocumentOrchestrator().issue(sale, cfg, seller, series="001-001", sequential="000000123")
    assert doc.document.series == "001-001"
    assert doc.document.sequential == "000000123"
    assert doc.totals.taxTotal == Decimal("12.00")


def test_template_engine_renders_basic_fields():
    cfg = TenantDocConfig(
        tax_profile={"DEFAULT": {"rate": 0, "code": "0"}},
        buyer_policy={"consumerFinalMaxTotal": 0},
    )
    sale = _build_sale(Decimal("10"))
    seller = SellerInfo(
        tenantId="tnt_123",
        tradeName="Mi Tienda",
        legalName="Mi Tienda",
        taxId="0999999999001",
        address="Calle 123",
        footerMessage="Gracias",
    )
    doc = DocumentOrchestrator().issue(sale, cfg, seller, series="001-001", sequential="000000001")
    html = TemplateEngine().render(doc)
    assert "Mi Tienda" in html
    assert "Gracias" in html


def test_document_model_includes_effective_from_and_version():
    cfg = TenantDocConfig(
        tax_profile={"DEFAULT": {"rate": 0, "code": "0"}},
        buyer_policy={"consumerFinalMaxTotal": 0},
        config_version=3,
        effective_from="2026-01-01",
    )
    sale = _build_sale(Decimal("5"))
    seller = SellerInfo(
        tenantId="tnt_123",
        tradeName="Mi Tienda",
        legalName="Mi Tienda",
        taxId="0999999999001",
        address="Calle 123",
    )
    doc = DocumentOrchestrator().issue(sale, cfg, seller, series="001-001", sequential="000000010")
    assert doc.document.meta["configEffectiveFrom"] == "2026-01-01"
    assert doc.document.meta["configVersion"] == 3
    assert doc.render.configEffectiveFrom == "2026-01-01"


def test_template_snapshot_ticket_80mm():
    cfg = TenantDocConfig(
        tax_profile={"DEFAULT": {"rate": 0, "code": "0"}},
        buyer_policy={"consumerFinalMaxTotal": 0},
        config_version=1,
        effective_from="2026-01-01",
    )
    sale = _build_sale(Decimal("10"))
    seller = SellerInfo(
        tenantId="tnt_123",
        tradeName="Mi Tienda",
        legalName="Mi Tienda",
        taxId="0999999999001",
        address="Calle 123",
        email="ventas@mitienda.ec",
        website="mitienda.ec",
    )
    doc = DocumentOrchestrator().issue(sale, cfg, seller, series="001-001", sequential="000000999")
    doc.document.issuedAt = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    html = TemplateEngine().render(doc)
    fixture = Path(__file__).parent / "fixtures" / "documents_ticket_80mm_v1.html"
    expected = fixture.read_text(encoding="utf-8")
    assert html == expected
