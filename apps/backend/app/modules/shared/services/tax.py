from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.company.company_settings import CompanySettings
from app.models.core.country_catalogs import CountryTaxCode
from app.models.tenant import Tenant

LEGACY_FALLBACK_TAX_RATE = Decimal("0.21")
_TAX_RATE_QUANT = Decimal("0.0001")


def normalize_tax_rate(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None

    try:
        rate = Decimal(str(value))
    except Exception:
        return None

    if rate < 0:
        rate = Decimal("0")
    if rate > 1:
        rate = rate / Decimal("100")
    return rate.quantize(_TAX_RATE_QUANT)


def resolve_country_tax_rates(db: Session, country_code: str | None) -> list[Decimal]:
    if not country_code:
        return []

    rows = (
        db.query(CountryTaxCode)
        .filter(
            CountryTaxCode.country_code == str(country_code).strip().upper(),
            CountryTaxCode.active.is_(True),
        )
        .order_by(CountryTaxCode.rate_default.desc(), CountryTaxCode.code.asc())
        .all()
    )

    rates: list[Decimal] = []
    seen: set[Decimal] = set()
    for row in rows:
        normalized = normalize_tax_rate(getattr(row, "rate_default", None))
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
        rates.append(normalized)
    return rates


def resolve_tenant_default_tax_rate(
    db: Session,
    tenant_id: UUID | str | None,
    *,
    fallback: Decimal = LEGACY_FALLBACK_TAX_RATE,
) -> Decimal:
    if tenant_id is None:
        return fallback

    tenant_key = str(tenant_id)
    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_key).first()

    candidates: list[Any] = []
    if settings:
        settings_blob = settings.settings if isinstance(settings.settings, dict) else {}
        pos_blob = settings.pos_config if isinstance(settings.pos_config, dict) else {}
        invoice_blob = settings.invoice_config if isinstance(settings.invoice_config, dict) else {}

        candidates.extend(
            [
                settings_blob.get("iva_tasa_defecto"),
                ((settings_blob.get("pos") or {}).get("tax") or {}).get("default_rate"),
                ((settings_blob.get("fiscal") or {}).get("tax") or {}).get("default_rate"),
                (pos_blob.get("tax") or {}).get("default_rate"),
                invoice_blob.get("default_tax_rate"),
            ]
        )

    for candidate in candidates:
        normalized = normalize_tax_rate(candidate)
        if normalized is not None:
            return normalized

    tenant = db.query(Tenant).filter(Tenant.id == tenant_key).first()
    country_rates = resolve_country_tax_rates(db, getattr(tenant, "country_code", None))
    if country_rates:
        return country_rates[0]

    return fallback
