from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.email.email_utils import enviar_correo_bienvenida
from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.company.company_user import CompanyUser
from app.models.core.modulo import CompanyModule, Module
from app.models.tenant import Tenant
from app.modules.empresa.application.use_cases import ListCompaniesAdmin, create_company_admin_user
from app.modules.empresa.infrastructure.repositories import SqlCompanyRepo
from app.modules.empresa.interface.http.schemas import CompanyInSchema, CompanyOutSchema
from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService
from app.shared.utils import slugify

router = APIRouter(
    prefix="/admin/companies",
    tags=["Admin Companies"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)

logger = logging.getLogger("app.company.admin")


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


@router.get("/{tenant_id}/settings")
def get_tenant_settings(tenant_id: str, db: Session = Depends(get_db)):
    """Retrieve full tenant settings"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant_not_found")

    # Get tenant_settings
    from app.models.core.settings import TenantSettings

    tenant_settings = db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()
    if not tenant_settings:
        tenant_settings = TenantSettings(tenant_id=tenant_id)
        db.add(tenant_settings)
        db.commit()
        db.refresh(tenant_settings)

    return {
        "locale": tenant_settings.locale,
        "timezone": tenant_settings.timezone,
        "currency": tenant_settings.currency,
        "sector_id": getattr(tenant, "sector_id", None),
        # Return both modern and legacy key for FE compatibility
        "sector_template_name": getattr(tenant, "sector_template_name", None),
        "sector_plantilla_name": getattr(tenant, "sector_template_name", None),
        "settings": tenant_settings.settings or {},
    }


@router.put("/{tenant_id}/settings")
def update_tenant_settings(tenant_id: str, settings: dict, db: Session = Depends(get_db)):
    """Update tenant settings"""
    from app.models.core.settings import TenantSettings

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant_not_found")

    # Get or create tenant_settings
    tenant_settings = db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()
    if not tenant_settings:
        tenant_settings = TenantSettings(tenant_id=tenant_id)
        db.add(tenant_settings)
        db.flush()

    # Update TenantSettings fields
    if "locale" in settings:
        tenant_settings.locale = settings["locale"]
    if "timezone" in settings:
        tenant_settings.timezone = settings["timezone"]
    if "currency" in settings:
        tenant_settings.currency = settings["currency"]

    # Persist sector metadata on tenant when provided
    if "sector_id" in settings:
        try:
            tenant.sector_id = (
                int(settings.get("sector_id")) if settings.get("sector_id") is not None else None
            )
        except Exception:
            tenant.sector_id = None
    # Accept both names for template name
    if (
        "sector_template_name" in settings
        or "sector_plantilla_nombre" in settings
        or "sector_plantilla_name" in settings
    ):
        tpl_name = settings.get("sector_template_name")
        if tpl_name is None:
            tpl_name = settings.get("sector_plantilla_nombre")
        if tpl_name is None:
            tpl_name = settings.get("sector_plantilla_name")
        tenant.sector_template_name = tpl_name

    # Merge other settings into JSONB (exclude keys handled above)
    other_settings = {
        k: v
        for k, v in settings.items()
        if k
        not in (
            "locale",
            "timezone",
            "currency",
            "sector_plantilla_id",
            "sector_id",
            "sector_template_name",
            "sector_plantilla_nombre",
            "sector_plantilla_name",
        )
    }
    if other_settings:
        current = tenant_settings.settings or {}
        current.update(other_settings)
        tenant_settings.settings = current

    # Apply sector template if provided
    sector_tpl_id = settings.get("sector_plantilla_id")
    if sector_tpl_id:
        try:
            from app.services.sector_templates import apply_sector_template

            apply_sector_template(
                db,
                tenant_id,
                int(sector_tpl_id),
                override_existing=True,
                design_only=True,
            )
        except Exception:
            pass

    db.commit()
    db.refresh(tenant_settings)

    return {
        "ok": True,
        "locale": tenant_settings.locale,
        "timezone": tenant_settings.timezone,
        "currency": tenant_settings.currency,
        "sector_id": getattr(tenant, "sector_id", None),
        # Return both keys for FE compatibility
        "sector_template_name": getattr(tenant, "sector_template_name", None),
        "sector_plantilla_name": getattr(tenant, "sector_template_name", None),
        "settings": tenant_settings.settings or {},
    }


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
        # Temporarily disable the trigger that blocks deleting the last admin
        db.execute(text("SET session_replication_role = replica;"))

        # Remove child records
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
            text("DELETE FROM company_users WHERE tenant_id::text = :tid"),
            {"tid": tenant_uuid},
        )
        db.execute(
            text("DELETE FROM company_roles WHERE tenant_id::text = :tid"),
            {"tid": tenant_uuid},
        )

        # Delete tenant (cascade via FK for other tables)
        db.execute(text("DELETE FROM tenants WHERE id::text = :tid"), {"tid": tenant_uuid})

        # Re-enable triggers
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
    logo: str | None = None
    primary_color: str | None = None
    active: bool | None = True
    deactivation_reason: str | None = None
    website: str | None = None
    config_json: dict | None = None


class CompanyFullIn(BaseModel):
    company: CompanyPayload
    admin: AdminUserIn
    modules: list[int] = Field(
        default_factory=list, validation_alias="modulos", serialization_alias="modulos"
    )
    logo: LogoPayload | None = None
    sector_plantilla_id: int | None = None  # Plantilla de sector a aplicar


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
    try:
        # Company (Tenant)
        repo = SqlCompanyRepo(db)
        company_data = payload.company.model_dump()
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

        # Módulos
        if tenant_uuid:
            for modulo_id in payload.modules or []:
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

        # AUTO-SETUP (con plantilla de sector opcional)
        if tid:
            try:
                from app.services.tenant_onboarding import auto_setup_tenant

                country = company_data.get("pais", "EC")
                setup_result = auto_setup_tenant(
                    db, tid, country, sector_plantilla_id=payload.sector_plantilla_id
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
        enviar_correo_bienvenida(user.email, user.username, payload.company.name, background_tasks)
    except Exception as e:
        # Do not interrupt the flow on SMTP failure, but log for diagnosis
        logger.warning("Failed to enqueue welcome email for %s: %s", user.email, e, exc_info=True)

    return {"msg": "ok", "id": tenant_uuid}
