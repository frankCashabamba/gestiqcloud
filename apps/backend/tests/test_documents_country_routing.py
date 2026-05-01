"""Country routing in DocumentOrchestrator: EC and ES are accepted, others fail."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.country_packs import supported_countries
from app.modules.documents.application.orchestrator import DocumentOrchestrator
from app.modules.documents.domain.config import TenantDocConfig
from app.modules.documents.domain.models import (
    BuyerIn,
    SaleDraft,
    SaleItemIn,
    SellerInfo,
)


def _seller() -> SellerInfo:
    return SellerInfo(
        tenantId="t1",
        tradeName="Trade",
        legalName="Legal",
        taxId="00000000T",
        address="Some address",
    )


def _draft(country: str, *, currency: str, buyer_id: str | None) -> SaleDraft:
    return SaleDraft(
        tenantId="t1",
        country=country,
        currency=currency,
        buyer=BuyerIn(
            mode="IDENTIFIED" if buyer_id else "CONSUMER_FINAL",
            idType="NIF" if country == "ES" else "RUC",
            idNumber=buyer_id,
            name="Buyer",
        ),
        items=[
            SaleItemIn(
                name="Producto",
                qty=Decimal("2"),
                unitPrice=Decimal("10.00"),
            )
        ],
    )


def test_supported_countries_includes_ec_and_es() -> None:
    assert "EC" in supported_countries()
    assert "ES" in supported_countries()


def test_orchestrator_routes_to_ecuador_pack() -> None:
    orch = DocumentOrchestrator()
    cfg = TenantDocConfig(country="EC", locale="es-EC")
    doc = orch.draft(_draft("EC", currency="USD", buyer_id=None), cfg, _seller())
    assert doc.info.country == "EC"
    assert orch.country_pack.countryCode == "EC"


def test_orchestrator_routes_to_espana_pack_with_valid_nif() -> None:
    orch = DocumentOrchestrator()
    cfg = TenantDocConfig(country="ES", locale="es-ES")
    doc = orch.draft(
        _draft("ES", currency="EUR", buyer_id="12345678Z"), cfg, _seller()
    )
    assert doc.info.country == "ES"
    assert orch.country_pack.countryCode == "ES"


def test_orchestrator_rejects_unsupported_country() -> None:
    orch = DocumentOrchestrator()
    cfg = TenantDocConfig(country="FR", locale="fr-FR")
    with pytest.raises(ValueError) as exc:
        orch.draft(_draft("FR", currency="EUR", buyer_id=None), cfg, _seller())
    assert "documents_country_not_supported" in str(exc.value)


def test_orchestrator_rejects_empty_country() -> None:
    orch = DocumentOrchestrator()
    cfg = TenantDocConfig(country="", locale="es-ES")
    with pytest.raises(ValueError):
        orch.draft(_draft("", currency="USD", buyer_id=None), cfg, _seller())
