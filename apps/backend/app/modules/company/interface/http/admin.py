from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import bindparam, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.api.email.email_utils import enviar_correo_bienvenida
from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.company.company import (
    Country,
    Currency,
    Language,
    RefLocale,
    RefTimezone,
    SectorPlantilla,
)
from app.models.company.company_settings import CompanySettings
from app.models.company.company_user import CompanyUser
from app.models.core.module import CompanyModule, Module
from app.models.tenant import Tenant
from app.modules.company.application.use_cases import ListCompaniesAdmin, create_company_admin_user
from app.modules.company.infrastructure.repositories import SqlCompanyRepo
from app.modules.company.interface.http.schemas import CompanyInSchema, CompanyOutSchema
from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService
from app.schemas.sector_plantilla import SectorConfigJSON
from app.shared.utils import slugify

router = APIRouter(
    prefix="/admin/companies",
    tags=["Admin Companies"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)

logger = logging.getLogger("app.company.admin")


def _collect_fk_tables(
    db: Session, referenced_table: str, schema: str = "public"
) -> list[tuple[str, str]]:
    rows = db.execute(
        text(
            """
            SELECT kcu.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND ccu.table_name = :ref_table
              AND tc.table_schema = :schema
            """
        ),
        {"ref_table": referenced_table, "schema": schema},
    ).all()
    return [(row[0], row[1]) for row in rows]


def _delete_company_data_postgres(
    db: Session, tenant_id: uuid.UUID, excluded_tables: set[str]
) -> None:
    schema = "public"
    user_fk_tables = _collect_fk_tables(db, "company_users", schema=schema)
    tenant_fk_tables = _collect_fk_tables(db, "tenants", schema=schema)

    # Delete rows that depend on company_users first to avoid FK violations.
    for table, column in user_fk_tables:
        if table in excluded_tables or table == "company_users":
            continue
        db.execute(
            text(
                f'DELETE FROM "{schema}"."{table}" '
                f'WHERE "{column}" IN (SELECT id FROM "{schema}"."company_users" WHERE tenant_id = :tenant_id)'
            ),
            {"tenant_id": tenant_id},
        )

    # Delete rows by tenant FK (skip tenants/company_users themselves).
    for table, column in tenant_fk_tables:
        if table in excluded_tables or table in ("tenants", "company_users"):
            continue
        db.execute(
            text(f'DELETE FROM "{schema}"."{table}" WHERE "{column}" = :tenant_id'),
            {"tenant_id": tenant_id},
        )


def _module_names(db: Session, tenant_id: uuid.UUID) -> list[str]:
    names: list[str] = []
    for cm, module_name in (
        db.query(CompanyModule, Module.name)
        .join(Module, CompanyModule.module_id == Module.id)
        .filter(CompanyModule.tenant_id == tenant_id, CompanyModule.active.is_(True))
        .all()
    ):
        if module_name:
            names.append(module_name)
    return names


def _pick_default_language(db: Session) -> str:
    locale = db.query(RefLocale).filter(RefLocale.active.is_(True)).first()
    if locale and locale.code:
        return locale.code
    language = db.query(Language).filter(Language.active.is_(True)).first()
    if language and language.code:
        return language.code
    raise HTTPException(status_code=400, detail="default_language_required")


def _pick_default_timezone(db: Session) -> str:
    timezone = db.query(RefTimezone).filter(RefTimezone.active.is_(True)).first()
    if timezone and timezone.name:
        return timezone.name
    raise HTTPException(status_code=400, detail="timezone_required")


def _pick_default_currency(db: Session) -> str:
    currency = db.query(Currency).filter(Currency.active.is_(True)).first()
    if currency and currency.code:
        return currency.code
    raise HTTPException(status_code=400, detail="currency_required")


@router.get("/{tenant_id}/pos/receipts/backfill_candidates", response_model=dict)
def admin_list_pos_backfill_candidates(
    tenant_id: str,
    request: Request,
    missing: str = "any",
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Lista receipts pagados que están incompletos (sin invoice y/o sin sales_order).

    `missing`:
      - any: falta invoice o sale
      - invoice: falta invoice
      - sale: falta sales_order
    """
    try:
        tenant_uuid = uuid.UUID(str(tenant_id))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_tenant_id")

    missing_norm = (missing or "any").strip().lower()
    if missing_norm not in ("any", "invoice", "sale"):
        raise HTTPException(status_code=400, detail="invalid_missing_filter")

    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200
    if offset < 0:
        offset = 0

    from app.db.rls import set_tenant_guc

    set_tenant_guc(db, str(tenant_uuid), persist=True)
    claims = getattr(request.state, "access_claims", {}) or {}
    if isinstance(claims, dict) and claims.get("user_id"):
        try:
            db.execute(text("SET app.user_id = :uid"), {"uid": str(claims["user_id"])})
        except Exception:
            pass

    tenant_currency_row = db.execute(
        text(
            """
            SELECT cs.currency, t.base_currency
            FROM tenants t
            LEFT JOIN company_settings cs ON cs.tenant_id = t.id
            WHERE t.id = :tid
            LIMIT 1
            """
        ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
        {"tid": tenant_uuid},
    ).first()
    tenant_currency: str | None = None
    if tenant_currency_row:
        cs_cur, base_cur = tenant_currency_row
        for val in (cs_cur, base_cur):
            if val:
                tenant_currency = str(val).strip().upper() or None
                if tenant_currency:
                    break

    where_parts: list[str] = ["r.status = 'paid'"]
    params: dict = {"tid": tenant_uuid, "limit": limit, "offset": offset}

    if since is not None:
        where_parts.append("r.paid_at >= :since")
        params["since"] = since
    if until is not None:
        where_parts.append("r.paid_at <= :until")
        params["until"] = until

    if missing_norm == "invoice":
        where_parts.append("r.invoice_id IS NULL")
    elif missing_norm == "sale":
        where_parts.append("so.id IS NULL")
    else:
        where_parts.append("(r.invoice_id IS NULL OR so.id IS NULL)")

    rows = db.execute(
        text(
            f"""
            SELECT
              r.id,
              r.number,
              r.paid_at,
              r.gross_total,
              r.tax_total,
              r.currency,
              r.invoice_id,
              so.id AS sales_order_id
            FROM pos_receipts r
            LEFT JOIN sales_orders so
              ON so.tenant_id = :tid
             AND so.pos_receipt_id = r.id
            WHERE {" AND ".join(where_parts)}
            ORDER BY r.paid_at DESC NULLS LAST, r.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ).bindparams(
            bindparam("tid", type_=PGUUID(as_uuid=True)),
        ),
        params,
    ).fetchall()

    items: list[dict] = []
    for (
        receipt_id,
        number,
        paid_at,
        gross_total,
        tax_total,
        currency,
        invoice_id,
        sales_order_id,
    ) in rows:
        receipt_currency = str(currency).strip().upper() if currency else None
        currency_mismatch = bool(
            tenant_currency and receipt_currency and receipt_currency != tenant_currency
        )
        items.append(
            {
                "receipt_id": str(receipt_id),
                "number": number,
                "paid_at": paid_at.isoformat()
                if hasattr(paid_at, "isoformat") and paid_at
                else None,
                "gross_total": float(gross_total or 0),
                "tax_total": float(tax_total or 0),
                # Nunca mostramos una moneda distinta a la configurada del tenant.
                "currency": None if currency_mismatch else receipt_currency,
                "tenant_currency": tenant_currency,
                "currency_mismatch": currency_mismatch,
                "invoice_id": str(invoice_id) if invoice_id else None,
                "sales_order_id": str(sales_order_id) if sales_order_id else None,
                "missing_invoice": invoice_id is None,
                "missing_sale": sales_order_id is None,
            }
        )

    return {
        "ok": True,
        "tenant_id": str(tenant_uuid),
        "tenant_currency": tenant_currency,
        "missing": missing_norm,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.post("/{tenant_id}/pos/receipts/{receipt_id}/backfill_documents", response_model=dict)
def admin_backfill_pos_receipt_documents(
    tenant_id: str,
    receipt_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Rescate/backfill POS (admin): reintenta crear invoice + sales_order desde un receipt paid.

    - Idempotente: si ya existen, no duplica.
    - Asegura tenant scope via Postgres GUC + RLS.
    """
    try:
        tenant_uuid = uuid.UUID(str(tenant_id))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_tenant_id")

    try:
        receipt_uuid = uuid.UUID(str(receipt_id))
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_receipt_id")

    from app.db.rls import set_tenant_guc

    set_tenant_guc(db, str(tenant_uuid), persist=True)
    claims = getattr(request.state, "access_claims", {}) or {}
    if isinstance(claims, dict) and claims.get("user_id"):
        try:
            db.execute(text("SET app.user_id = :uid"), {"uid": str(claims["user_id"])})
        except Exception:
            pass

    receipt = db.execute(
        text(
            """
            SELECT status
            FROM pos_receipts
            WHERE id = :id
            FOR UPDATE
            """
        ).bindparams(bindparam("id", type_=PGUUID(as_uuid=True))),
        {"id": receipt_uuid},
    ).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="receipt_not_found")
    if receipt[0] != "paid":
        raise HTTPException(status_code=400, detail="invalid_status")

    documents_created: dict = {}
    try:
        from app.modules.pos.application.invoice_integration import POSInvoicingService

        service = POSInvoicingService(db, tenant_uuid)

        # Try to create invoice
        try:
            invoice_result = service.create_invoice_from_receipt(receipt_uuid, customer_id=None)
            if invoice_result:
                documents_created["invoice"] = invoice_result
        except Exception as e:
            logger.warning("Failed to create invoice for receipt %s: %s", receipt_uuid, e)
            # Reset transaction state before trying next operation
            db.rollback()

        # Try to create sale order
        try:
            sale_result = service.create_sale_from_receipt(receipt_uuid)
            if sale_result:
                documents_created["sale"] = sale_result
        except Exception as e:
            logger.warning("Failed to create sale for receipt %s: %s", receipt_uuid, e)
            db.rollback()
    except Exception as e:
        logger.exception("Unexpected error in POS backfill: %s", e)
        db.rollback()

    return {"ok": True, "receipt_id": str(receipt_uuid), "documents_created": documents_created}


@router.get("", response_model=list[CompanyOutSchema])
def list_companies_admin(db: Session = Depends(get_db)) -> list[CompanyOutSchema]:
    use = ListCompaniesAdmin(SqlCompanyRepo(db))
    items = use.execute()
    out: list[CompanyOutSchema] = []
    for i in items:
        tenant_uuid = i.get("id")
        mod_names = _module_names(db, tenant_uuid) if tenant_uuid else []
        enriched = {**i, "modules": mod_names}
        out.append(CompanyOutSchema.model_validate(enriched))
    return out


@router.get("/{tenant_id}", response_model=CompanyOutSchema)
def get_company_admin(tenant_id: str, db: Session = Depends(get_db)) -> CompanyOutSchema:
    repo = SqlCompanyRepo(db)
    item = repo.get(id=tenant_id)
    if not item:
        raise HTTPException(status_code=404, detail="company_not_found")
    # Enrich with modules as in the list endpoint
    mod_names = []
    try:
        tenant_uuid = uuid.UUID(str(tenant_id))
        mod_names = _module_names(db, tenant_uuid)
    except Exception:
        mod_names = []
    enriched = {**item, "modules": mod_names}
    return CompanyOutSchema.model_validate(enriched)


@router.put("/{tenant_id}", response_model=CompanyOutSchema)
def update_company(tenant_id: str, payload: CompanyInSchema, db: Session = Depends(get_db)):
    repo = SqlCompanyRepo(db)
    updated = repo.update(tenant_id, payload.model_dump(by_alias=True))
    if not updated:
        raise HTTPException(status_code=404, detail="company_not_found")
    return CompanyOutSchema.model_construct(**updated)


@router.post("/{tenant_id}/impersonate")
def impersonate_tenant(tenant_id: str, db: Session = Depends(get_db)):
    """Generate an impersonation access token to open the tenant PWA."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant_not_found")
    svc = PyJWTTokenService()
    claims = {
        "tenant_id": str(tenant.id),
        "scope": "impersonate",
        "kind": "tenant",
        # user_id opcional; dejamos None para un contexto técnico de administración
    }
    token = svc.issue_access(claims)
    return {"access_token": token, "tenant_slug": getattr(tenant, "slug", None)}


@router.delete("/{tenant_id}")
def delete_company(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(with_access_claims),
):
    """
    Delete a company and all related records in cascade.
    Everything is logged for full traceability.
    """
    from app.services.audit_service import AuditService, serialize_model

    company = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="company_not_found")

    company_data = serialize_model(company)

    tenant_uuid = str(company.id)

    # Collect related data before deletion
    related_data = {}

    try:
        # Users
        users = (
            db.execute(
                text("SELECT * FROM company_users WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid},
            )
            .mappings()
            .all()
        )
        related_data["users"] = [dict(row) for row in users]

        # Products
        products = (
            db.execute(
                text("SELECT * FROM products WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid},
            )
            .mappings()
            .all()
        )
        related_data["products"] = [dict(row) for row in products]

        # Invoices (if the table exists)
        try:
            facturas = (
                db.execute(
                    text("SELECT * FROM invoices WHERE tenant_id::text = :tid"),
                    {"tid": tenant_uuid},
                )
                .mappings()
                .all()
            )
            related_data["invoices"] = [dict(row) for row in facturas]
        except Exception:
            related_data["invoices"] = []

        # Clients (new table name assumed)
        try:
            clients = (
                db.execute(
                    text("SELECT * FROM clients WHERE tenant_id::text = :tid"),
                    {"tid": tenant_uuid},
                )
                .mappings()
                .all()
            )
            related_data["clients"] = [dict(row) for row in clients]
        except Exception:
            related_data["clients"] = []

        # Assigned modules
        assigned_modules = (
            db.execute(
                text("SELECT * FROM assigned_modules WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid},
            )
            .mappings()
            .all()
        )
        related_data["assigned_modules"] = [dict(row) for row in assigned_modules]

        # Company modules
        company_modules = (
            db.execute(
                text("SELECT * FROM company_modules WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid},
            )
            .mappings()
            .all()
        )
        related_data["company_modules"] = [dict(row) for row in company_modules]

        # Roles
        roles = (
            db.execute(
                text("SELECT * FROM company_roles WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid},
            )
            .mappings()
            .all()
        )
        related_data["roles"] = [dict(row) for row in roles]

        # User roles
        user_roles = (
            db.execute(
                text("SELECT * FROM company_user_roles WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid},
            )
            .mappings()
            .all()
        )
        related_data["user_roles"] = [dict(row) for row in user_roles]

    except Exception as e:
        logger.warning(f"Error collecting related data: {e}")
        related_data["error"] = str(e)
        db.rollback()  # Roll back to avoid aborted transaction state

    # Audit before deleting
    user_email = current_user.get("email") or current_user.get("sub")
    user_id = current_user.get("user_id")

    AuditService.log_delete_company(
        db=db,
        company_data=company_data,
        related_data=related_data,
        user_id=user_id,
        user_email=user_email,
        user_role="admin",
        ip_address=None,  # Could be obtained from request if needed
        tenant_uuid=uuid.UUID(tenant_uuid),
        tenant_legacy_id=None,
    )

    # Now proceed with cascade deletion
    try:
        dialect = getattr(db.get_bind().dialect, "name", "")
        role_changed = False
        if dialect == "postgresql":
            # Temporarily disable triggers that can block admin deletion.
            # En entornos gestionados (Render, RDS, etc.) la credencial app no es superuser
            # y SET session_replication_role falla; continuamos sin abortar el borrado.
            try:
                db.execute(text("SET session_replication_role = replica;"))
                role_changed = True
            except Exception as e:
                logger.warning("No se pudo desactivar triggers (continuando): %s", e)

        excluded_tables = {"audit_events", "auth_audit"}

        if dialect == "postgresql":
            _delete_company_data_postgres(db, uuid.UUID(tenant_uuid), excluded_tables)
            db.execute(
                text('DELETE FROM "public"."company_users" WHERE tenant_id = :tenant_id'),
                {"tenant_id": uuid.UUID(tenant_uuid)},
            )
            db.execute(
                text('DELETE FROM "public"."tenants" WHERE id = :tenant_id'),
                {"tenant_id": uuid.UUID(tenant_uuid)},
            )
        else:
            # Fallback for non-Postgres: explicit deletes for core tables.
            db.execute(
                text("DELETE FROM company_user_roles WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid},
            )
            db.execute(
                text("DELETE FROM assigned_modules WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid},
            )
            db.execute(
                text("DELETE FROM company_modules WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid},
            )
            db.execute(
                text("DELETE FROM user_profiles WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid},
            )
            db.execute(
                text("DELETE FROM company_users WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid},
            )
            db.execute(
                text("DELETE FROM company_roles WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid},
            )
            db.execute(text("DELETE FROM tenants WHERE id::text = :tid"), {"tid": tenant_uuid})

        if dialect == "postgresql" and role_changed:
            # Re-enable triggers solo si logramos cambiarlas
            db.execute(text("SET session_replication_role = DEFAULT;"))

        db.commit()

        logger.info(f"✅ Company {tenant_id} deleted with audit trail")

        return {
            "ok": True,
            "tenant_id": tenant_uuid,
            "name": company_data.get("name"),
            "deleted_records": {key: len(value) for key, value in related_data.items()},
        }

    except Exception as e:
        # Re-enable triggers before rollback
        try:
            if getattr(db.get_bind().dialect, "name", "") == "postgresql" and role_changed:
                db.execute(text("SET session_replication_role = DEFAULT;"))
        except Exception:
            pass
        db.rollback()
        logger.error(f"Error deleting company {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"error_deleting_company: {str(e)}")


class AdminUserIn(BaseModel):
    first_name: str
    last_name: str
    email: str
    username: str
    password: str | None = None


class AdminUserOut(BaseModel):
    id: int
    email: str
    username: str


class LogoPayload(BaseModel):
    data: str  # base64 (o data URL con prefix)
    filename: str | None = None
    content_type: str | None = None


class CompanyPayload(BaseModel):
    name: str
    initial_template: str
    slug: str | None = None
    tax_id: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    cp: str | None = None
    country: str | None = None
    country_code: str | None = None
    logo: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    active: bool | None = True
    deactivation_reason: str | None = None
    website: str | None = None
    config_json: dict | None = None
    default_language: str | None = None
    timezone: str | None = None
    currency: str | None = None
    base_currency: str | None = None


class CompanyFullIn(BaseModel):
    company: CompanyPayload
    admin: AdminUserIn
    modules: list[uuid.UUID] = Field(
        default_factory=list, validation_alias="modulos", serialization_alias="modulos"
    )
    logo: LogoPayload | None = None
    sector_template_id: uuid.UUID | None = Field(
        default=None,
        validation_alias="sector_plantilla_id",
        serialization_alias="sector_plantilla_id",
    )  # Plantilla de sector a aplicar

    @field_validator("modules", mode="before")
    @classmethod
    def _coerce_modules(cls, v: object) -> list[uuid.UUID]:
        """
        Acepta módulos como UUID, str o int (legacy) y los normaliza a UUID.
        Evita errores de validación cuando el FE envía strings.
        """
        if v is None:
            return []
        items = v if isinstance(v, list) else [v]
        normalized: list[uuid.UUID] = []
        for item in items:
            if item is None or item == "":
                continue
            try:
                normalized.append(uuid.UUID(str(item)))
            except Exception as exc:  # pragma: no cover - defensive
                raise ValueError("invalid_module_id") from exc
        return normalized


def _decode_data_url(data: str) -> tuple[bytes, str | None]:
    import base64
    import re

    if data.startswith("data:"):
        m = re.match(r"^data:([^;,]+);base64,(.*)$", data, re.IGNORECASE | re.DOTALL)
        if not m:
            raise ValueError("invalid_data_url")
        mime = m.group(1)
        b = base64.b64decode(m.group(2))
        return b, mime
    else:
        b = base64.b64decode(data)
        return b, None


@router.post("/full-json")
async def create_company_full_json(
    payload: CompanyFullIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Unicidad básica
    if payload.company.tax_id:
        exists_ruc = db.query(Tenant).filter(Tenant.tax_id == payload.company.tax_id).first()
        if exists_ruc:
            raise HTTPException(status_code=400, detail="company_tax_id_exists")

    email_clean = (str(payload.admin.email) or "").strip().lower()
    username_clean = (payload.admin.username or "").strip().lower()

    # Autogenera username si no viene: nombre.apellido (normalizado), garantizando unicidad
    if not username_clean:
        try:
            first = slugify(payload.admin.first_name or "", separator="")
            last = slugify(payload.admin.last_name or "", separator="")
            base = ".".join([p for p in [first, last] if p]).strip(".")
            if not base:
                base = (email_clean.split("@")[0] or "usuario").strip(".")
            candidate = base.lower()
            # si existe, agrega sufijos incrementales
            i = 1
            while (
                db.query(CompanyUser).filter(func.lower(CompanyUser.username) == candidate).first()
            ):
                i += 1
                candidate = f"{base}{i}".lower()
            username_clean = candidate
        except Exception:
            # fallback mínimo
            username_clean = (email_clean.split("@")[0] or "usuario").lower()

    # Verificación de unicidad email/username definitivos (con rollback defensivo si la sesión viene abortada)
    if email_clean or username_clean:
        try:
            # Si una operación previa en esta request abortó la transacción, limpia antes de consultar
            try:
                db.rollback()
            except Exception:
                pass
            exists_user = (
                db.query(CompanyUser)
                .filter(
                    (func.lower(CompanyUser.email) == email_clean)
                    | (func.lower(CompanyUser.username) == username_clean)
                )
                .first()
            )
            if exists_user:
                raise HTTPException(status_code=400, detail="user_email_or_username_taken")
        except Exception as e:
            # Limpia el estado abortado y devuelve un error claro
            try:
                db.rollback()
            except Exception:
                pass
            logger.exception("DB error during uniqueness check")
            raise HTTPException(status_code=400, detail="db_error_check_user_unique") from e

    tenant_uuid: uuid.UUID | None = None
    default_language = payload.company.default_language
    timezone = payload.company.timezone
    currency = payload.company.currency or payload.company.base_currency
    country_code = payload.company.country_code
    primary_color = payload.company.primary_color
    secondary_color = payload.company.secondary_color

    if payload.sector_template_id:
        sector = db.get(SectorPlantilla, payload.sector_template_id)
        if not sector:
            raise HTTPException(status_code=400, detail="sector_template_not_found")
        try:
            config = SectorConfigJSON(**(sector.template_config or {}))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="sector_template_invalid") from exc
        primary_color = config.branding.color_primario
        secondary_color = config.branding.color_secundario

    if not primary_color:
        raise HTTPException(status_code=400, detail="primary_color_required")
    if not secondary_color:
        raise HTTPException(status_code=400, detail="secondary_color_required")

    if not default_language:
        raise HTTPException(status_code=400, detail="default_language_required")

    if not timezone:
        raise HTTPException(status_code=400, detail="timezone_required")

    if not currency:
        raise HTTPException(status_code=400, detail="currency_required")

    if default_language:
        locale_exists = (
            db.query(RefLocale)
            .filter(RefLocale.code == default_language, RefLocale.active.is_(True))
            .first()
        )
        language_exists = (
            db.query(Language)
            .filter(Language.code == default_language, Language.active.is_(True))
            .first()
        )
        if not locale_exists and not language_exists:
            raise HTTPException(status_code=400, detail="default_language_not_found")

    if timezone:
        tz_exists = (
            db.query(RefTimezone)
            .filter(RefTimezone.name == timezone, RefTimezone.active.is_(True))
            .first()
        )
        if not tz_exists:
            raise HTTPException(status_code=400, detail="timezone_not_found")

    if currency:
        currency_exists = (
            db.query(Currency).filter(Currency.code == currency, Currency.active.is_(True)).first()
        )
        if not currency_exists:
            raise HTTPException(status_code=400, detail="currency_not_found")

    if country_code:
        country_exists = (
            db.query(Country).filter(Country.code == country_code, Country.active.is_(True)).first()
        )
        if not country_exists:
            raise HTTPException(status_code=400, detail="country_code_not_found")
    try:
        # Company (Tenant)
        repo = SqlCompanyRepo(db)
        company_data = payload.company.model_dump()
        company_data["primary_color"] = primary_color
        if not company_data.get("slug"):
            company_data["slug"] = slugify(company_data.get("name") or "")
        created_company = repo.create(company_data)
        tenant_uuid = created_company.get("id")

        # Logo opcional
        if payload.logo is not None and payload.logo.data:
            raw, mime = _decode_data_url(payload.logo.data)
            ext = None
            if payload.logo.filename and "." in payload.logo.filename:
                ext = os.path.splitext(payload.logo.filename)[1]
            if not ext and (payload.logo.content_type or mime):
                ct = (payload.logo.content_type or mime or "").lower()
                if ct.endswith("png"):
                    ext = ".png"
                elif ct.endswith("jpeg") or ct.endswith("jpg"):
                    ext = ".jpg"
                elif ct.endswith("webp"):
                    ext = ".webp"
            if not ext:
                ext = ".png"
            base_dir = Path(os.getcwd()) / "uploads" / "logos"
            base_dir.mkdir(parents=True, exist_ok=True)
            fname = f"{uuid.uuid4().hex}{ext}"
            dest = base_dir / fname
            dest.write_bytes(raw)
            repo.update(tenant_uuid, {"logo": f"/uploads/logos/{fname}"})

        # Auto-asignación de plantilla y fijar contexto RLS ANTES de crear usuario
        tid = str(tenant_uuid) if tenant_uuid else None

        import secrets

        tmp_password = payload.admin.password or secrets.token_urlsafe(24)
        user = create_company_admin_user(
            db,
            tenant_id=tenant_uuid,
            first_name=payload.admin.first_name,
            last_name=payload.admin.last_name,
            email=email_clean,
            username=username_clean,
            password=tmp_password,
        )

        # Módulos: Solo asignar los explícitamente contratados por la empresa
        # Validar que se contrate al menos 1 módulo
        if not payload.modules or len(payload.modules) == 0:
            raise HTTPException(status_code=400, detail="at_least_one_module_required")

        if tenant_uuid:
            for modulo_id in payload.modules:
                exists_module = (
                    db.query(CompanyModule)
                    .filter(
                        CompanyModule.tenant_id == tenant_uuid,
                        CompanyModule.module_id == modulo_id,
                    )
                    .first()
                )
                if exists_module:
                    continue
                db.add(
                    CompanyModule(
                        tenant_id=tenant_uuid,
                        module_id=modulo_id,
                        active=True,
                    )
                )

        if tenant_uuid:
            default_language_value = default_language
            timezone_value = timezone
            currency_value = currency
            company_settings = (
                db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_uuid).first()
            )
            if not company_settings:
                company_settings = CompanySettings(
                    tenant_id=tenant_uuid,
                    default_language=default_language_value,
                    timezone=timezone_value,
                    currency=currency_value,
                    primary_color=primary_color,
                    secondary_color=secondary_color,
                )
                db.add(company_settings)
                db.flush()
            else:
                company_settings.default_language = default_language_value
                company_settings.timezone = timezone_value
                company_settings.currency = currency_value
                company_settings.primary_color = primary_color
                company_settings.secondary_color = secondary_color

        # AUTO-SETUP (con plantilla de sector opcional)
        if tid:
            try:
                from app.services.tenant_onboarding import auto_setup_tenant

                country = company_data.get("country_code") or company_data.get("country")
                setup_result = auto_setup_tenant(
                    db, tid, country, sector_template_id=payload.sector_template_id
                )
                logger.info(f"✅ Tenant auto-setup: {setup_result}")
            except Exception as e:
                logger.warning(f"⚠️ Auto-setup parcial: {e}")

        db.commit()
    except HTTPException:
        db.rollback()
        if tenant_uuid:
            try:
                db.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tenant_uuid})
                db.commit()
            except Exception:
                db.rollback()
        raise
    except Exception as e:
        db.rollback()
        if tenant_uuid:
            try:
                db.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tenant_uuid})
                db.commit()
            except Exception:
                db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    try:
        enviar_correo_bienvenida(
            user_email=user.email,
            username=user.username,
            empresa_nombre=payload.company.name,
            background_tasks=background_tasks,
            nombre_usuario=f"{payload.admin.first_name} {payload.admin.last_name}".strip(),
            is_admin_company=user.is_company_admin,
        )
    except Exception as e:
        # Do not interrupt the flow on SMTP failure, but log for diagnosis
        logger.warning("Failed to enqueue welcome email for %s: %s", user.email, e, exc_info=True)

    return {"msg": "ok", "id": tenant_uuid}
