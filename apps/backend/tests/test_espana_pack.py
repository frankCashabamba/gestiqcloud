"""Unit tests for EspanaPack: NIF/NIE/CIF validation and IVA defaults."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.country_packs.espana import (
    EspanaPack,
    default_tax_rates,
    validate_tax_id,
)
from app.modules.documents.domain.config import TenantDocConfig
from app.modules.documents.domain.models import BuyerIn, SaleDraft, SaleItemIn


# ---------------------------------------------------------------------------
# Tax-ID validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "12345678Z",   # DNI válido (12345678 % 23 = 14 -> 'Z')
        "00000000T",   # 0 % 23 = 0 -> 'T'
        "X1234567L",   # NIE válido (01234567 % 23 = 11 -> 'L')
        "B12345674",   # CIF organización con dígito de control numérico
    ],
)
def test_validate_tax_id_valid(value: str) -> None:
    assert validate_tax_id(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        "12345678A",   # letra incorrecta
        "1234567Z",    # demasiado corto
        "X1234567A",   # NIE letra incorrecta
        "B12345670",   # CIF con dígito de control inválido
        "INVALID00",
    ],
)
def test_validate_tax_id_invalid(value) -> None:
    assert validate_tax_id(value) is False


# ---------------------------------------------------------------------------
# Default IVA rates
# ---------------------------------------------------------------------------


def test_default_tax_rates_match_spain() -> None:
    rates = default_tax_rates()
    assert rates["GENERAL"] == Decimal("0.21")
    assert rates["REDUCED"] == Decimal("0.10")
    assert rates["SUPER_REDUCED"] == Decimal("0.04")
    assert rates["EXEMPT"] == Decimal("0")


# ---------------------------------------------------------------------------
# Pack metadata + validate()
# ---------------------------------------------------------------------------


def test_pack_metadata() -> None:
    pack = EspanaPack()
    assert pack.countryCode == "ES"
    assert pack.currency == "EUR"


def _draft(buyer_id: str | None = None, currency: str = "EUR") -> SaleDraft:
    return SaleDraft(
        tenantId="t1",
        country="ES",
        currency=currency,
        buyer=BuyerIn(
            mode="IDENTIFIED" if buyer_id else "CONSUMER_FINAL",
            idType="NIF",
            idNumber=buyer_id,
            name="Test",
        ),
        items=[SaleItemIn(name="Item", qty=Decimal("1"), unitPrice=Decimal("10"))],
    )


def test_validate_rejects_non_eur_currency() -> None:
    pack = EspanaPack()
    cfg = TenantDocConfig(country="ES", locale="es-ES")
    errs = pack.validate(_draft(buyer_id="12345678Z", currency="USD"), cfg)
    codes = {e.code for e in errs}
    assert "invalid_currency" in codes


def test_validate_rejects_invalid_tax_id() -> None:
    pack = EspanaPack()
    cfg = TenantDocConfig(country="ES", locale="es-ES")
    errs = pack.validate(_draft(buyer_id="12345678A"), cfg)
    codes = {e.code for e in errs}
    assert "invalid_tax_id" in codes


def test_validate_passes_for_valid_identified_buyer() -> None:
    pack = EspanaPack()
    cfg = TenantDocConfig(country="ES", locale="es-ES")
    errs = pack.validate(_draft(buyer_id="12345678Z"), cfg)
    assert errs == []


# ---------------------------------------------------------------------------
# calculate_line_taxes
# ---------------------------------------------------------------------------


def test_calculate_line_taxes_uses_profile_rate() -> None:
    pack = EspanaPack()
    cfg = TenantDocConfig(
        country="ES",
        tax_profile={"DEFAULT": {"rate": "21", "code": "IVA21"}},
    )
    lines = pack.calculate_line_taxes(
        line_subtotal=Decimal("100.00"), tax_category="DEFAULT", cfg=cfg
    )
    assert len(lines) == 1
    assert lines[0].rate == Decimal("0.21")
    assert lines[0].amount == Decimal("21.00")
    assert lines[0].code == "IVA21"


def test_calculate_line_taxes_falls_back_to_general() -> None:
    pack = EspanaPack()
    cfg = TenantDocConfig(country="ES")
    lines = pack.calculate_line_taxes(
        line_subtotal=Decimal("50.00"), tax_category="DEFAULT", cfg=cfg
    )
    assert lines[0].rate == Decimal("0.21")
    assert lines[0].amount == Decimal("10.50")
