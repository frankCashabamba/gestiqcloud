from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.company.company_settings import CompanySettings
from app.models.tenant import Tenant
from app.modules.documents.domain.config import TenantDocConfig


def load_tenant_doc_config(db: Session, tenant_id: str) -> TenantDocConfig:
    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()

    cfg = TenantDocConfig()
    if tenant and tenant.country_code:
        cfg.country = tenant.country_code
    if settings and isinstance(settings.settings, dict):
        doc_cfg = settings.settings.get("documents") or {}
        if isinstance(doc_cfg, dict):
            cfg.country = doc_cfg.get("country", cfg.country)
            cfg.document_mode_default = doc_cfg.get(
                "document_mode_default", cfg.document_mode_default
            )
            cfg.render_format_default = doc_cfg.get(
                "render_format_default", cfg.render_format_default
            )
            cfg.buyer_policy = doc_cfg.get("buyer_policy", cfg.buyer_policy)
            cfg.tax_profile = doc_cfg.get("tax_profile", cfg.tax_profile)
            cfg.branding = doc_cfg.get("branding", cfg.branding)
            cfg.template_overrides = doc_cfg.get("template_overrides", cfg.template_overrides)
            cfg.locale = doc_cfg.get("locale", cfg.locale)
            cfg.config_version = int(doc_cfg.get("version", cfg.config_version))
            cfg.effective_from = doc_cfg.get("effectiveFrom", cfg.effective_from)

    if settings and settings.invoice_config and isinstance(settings.invoice_config, dict):
        inv = settings.invoice_config
        cfg.buyer_policy = inv.get("buyer_policy", cfg.buyer_policy)
        cfg.tax_profile = inv.get("tax_profile", cfg.tax_profile)

    # Load country catalogs (id types + tax codes)
    try:
        id_rows = db.execute(
            text("SELECT code FROM country_id_types " "WHERE country_code = :cc AND active = true"),
            {"cc": cfg.country},
        ).fetchall()
        cfg.id_types = [r[0] for r in id_rows if r and r[0]]

        tax_rows = db.execute(
            text(
                "SELECT code, name, rate_default FROM country_tax_codes "
                "WHERE country_code = :cc AND active = true"
            ),
            {"cc": cfg.country},
        ).fetchall()
        cfg.tax_codes = {
            r[0]: {"name": r[1], "rate": float(r[2]) if r[2] is not None else None}
            for r in tax_rows
            if r and r[0]
        }
    except Exception:
        # Catalogs are optional; do not break flow if tables are missing.
        cfg.id_types = cfg.id_types or []
        cfg.tax_codes = cfg.tax_codes or {}

    if not cfg.tax_profile:
        cfg.tax_profile = {"DEFAULT": {"rate": 0, "code": "0"}}
    if not cfg.buyer_policy:
        cfg.buyer_policy = {
            "consumerFinalEnabled": True,
            "consumerFinalMaxTotal": 0,
            "requireBuyerAboveAmount": False,
        }

    return cfg


def build_seller_info(db: Session, tenant_id: str, branding: dict | None) -> dict:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    trade_name = (
        (branding or {}).get("tradeName")
        or (settings.company_name if settings else None)
        or (tenant.name if tenant else "")
    )
    legal_name = (branding or {}).get("legalName") or trade_name
    tax_id = (
        (branding or {}).get("taxId")
        or (settings.tax_id if settings else None)
        or ((tenant.tax_id if tenant else None) or "")
    )
    address = (branding or {}).get("address") or ((tenant.address if tenant else None) or "")
    logo = (branding or {}).get("logo") or (settings.company_logo if settings else None)
    email = (branding or {}).get("email")
    website = (branding or {}).get("website") or (tenant.website if tenant else None)
    footer = (branding or {}).get("footer") or (branding or {}).get("footerMessage")
    return {
        "tenantId": tenant_id,
        "tradeName": trade_name or "",
        "legalName": legal_name or (trade_name or ""),
        "taxId": tax_id or "",
        "address": address or "",
        "logo": logo,
        "email": email,
        "website": website,
        "footerMessage": footer,
    }
