from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from slugify import slugify
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.email.email_utils import enviar_correo_bienvenida
from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.empresa.usuarioempresa import UsuarioEmpresa
from app.models.tenant import Tenant as Empresa
from app.modules import crud as mod_crud
from app.modules import schemas as mod_schemas
from app.modules import services as mod_services
from app.modules.empresa.application.use_cases import ListarEmpresasAdmin, crear_usuario_admin
from app.modules.empresa.infrastructure.repositories import SqlEmpresaRepo
from app.modules.empresa.interface.http.schemas import EmpresaInSchema, EmpresaOutSchema
from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService

router = APIRouter(
    prefix="/admin/empresas",
    tags=["Admin Empresas"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)

logger = logging.getLogger("app.empresa.admin")


@router.get("", response_model=list[EmpresaOutSchema])
def listar_empresas_admin(db: Session = Depends(get_db)) -> list[EmpresaOutSchema]:
    use = ListarEmpresasAdmin(SqlEmpresaRepo(db))
    items = use.execute()
    out: list[EmpresaOutSchema] = []
    for i in items:
        tenant_uuid = i.get("id")
        empresa_id = None
        if tenant_uuid is not None:
            try:
                row = db.execute(
                    text("SELECT slug FROM tenants WHERE tenant_id =:id"),
                    {"id": str(tenant_uuid)},
                ).first()
                empresa_id = int(row[0]) if row and row[0] is not None else None
            except Exception:
                empresa_id = None
        mod_names: list[str] = []
        if empresa_id is not None:
            try:
                registros = mod_crud.obtener_modulos_de_empresa(db, empresa_id)
                mod_names = [
                    getattr(r.modulo, "name", None) for r in registros if getattr(r, "modulo", None)
                ]
            except Exception:
                mod_names = []
        enriched = {**i, "modulos": mod_names}
        out.append(EmpresaOutSchema.model_validate(enriched))
    return out


@router.get("/{tenant_id}", response_model=EmpresaOutSchema)
def obtener_empresa_admin(tenant_id: str, db: Session = Depends(get_db)) -> EmpresaOutSchema:
    repo = SqlEmpresaRepo(db)
    item = repo.get(id=tenant_id)
    if not item:
        raise HTTPException(status_code=404, detail="empresa_not_found")
    # Enriquecer con modulos como en el listado
    try:
        registros = mod_crud.obtener_modulos_de_empresa(db, tenant_id)
        mod_names = [
            getattr(r.modulo, "name", None) for r in registros if getattr(r, "modulo", None)
        ]
    except Exception:
        mod_names = []
    enriched = {**item, "modulos": mod_names}
    return EmpresaOutSchema.model_validate(enriched)


@router.put("/{tenant_id}", response_model=EmpresaOutSchema)
def actualizar_empresa(tenant_id: str, payload: EmpresaInSchema, db: Session = Depends(get_db)):
    repo = SqlEmpresaRepo(db)
    updated = repo.update(tenant_id, payload.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="empresa_not_found")
    return EmpresaOutSchema.model_construct(**updated)


@router.get("/{tenant_id}/settings")
def get_tenant_settings(tenant_id: str, db: Session = Depends(get_db)):
    """Obtener configuración completa del tenant"""
    tenant = db.query(Empresa).filter(Empresa.id == tenant_id).first()
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
    """Actualizar configuración del tenant"""
    from app.models.core.settings import TenantSettings

    tenant = db.query(Empresa).filter(Empresa.id == tenant_id).first()
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
    """Genera un access token de impersonación para abrir la PWA del tenant.

    Devuelve { access_token, tenant_slug }. El FE abrirá `/:slug#access_token=...` en la PWA.
    """
    tenant = db.query(Empresa).filter(Empresa.id == tenant_id).first()
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
def eliminar_empresa(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(with_access_claims),
):
    """
    Elimina una empresa y TODOS sus datos relacionados en cascada.
    Registra todo en audit_log para trazabilidad completa.
    """
    from app.services.audit_service import AuditService, serialize_model

    # Obtener empresa completa antes de borrar
    empresa = db.query(Empresa).filter(Empresa.id == tenant_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="empresa_not_found")

    empresa_data = serialize_model(empresa)

    # Obtener tenant_id
    tenant = db.execute(
        text("SELECT id::text, slug FROM tenants WHERE tenant_id = :eid"),
        {"eid": tenant_id},
    ).first()
    tenant_uuid = tenant[0] if tenant else None

    # Recolectar datos relacionados ANTES de borrar
    related_data = {}

    try:
        # Usuarios
        usuarios = (
            db.execute(
                text("SELECT * FROM usuarios_usuarioempresa WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid} if tenant_uuid else {"tid": None},
            )
            .mappings()
            .all()
        )
        related_data["usuarios"] = [dict(row) for row in usuarios]

        # Productos
        productos = (
            db.execute(
                text("SELECT * FROM products WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid} if tenant_uuid else {"tid": None},
            )
            .mappings()
            .all()
        )
        related_data["productos"] = [dict(row) for row in productos]

        # Facturas (si existe la tabla)
        try:
            facturas = (
                db.execute(
                    text("SELECT * FROM invoices WHERE tenant_id::text = :tid"),
                    {"tid": tenant_uuid} if tenant_uuid else {"tid": None},
                )
                .mappings()
                .all()
            )
            related_data["facturas"] = [dict(row) for row in facturas]
        except Exception:
            related_data["facturas"] = []

        # Clientes
        clientes = (
            db.execute(
                text("SELECT * FROM clientes_clienteempresa WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid} if tenant_uuid else {"tid": None},
            )
            .mappings()
            .all()
        )
        related_data["clientes"] = [dict(row) for row in clientes]

        # Módulos asignados
        modulos = (
            db.execute(
                text("SELECT * FROM modulos_empresamodulo WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid} if tenant_uuid else {"tid": None},
            )
            .mappings()
            .all()
        )
        related_data["modulos"] = [dict(row) for row in modulos]

        # Roles
        roles = (
            db.execute(
                text("SELECT * FROM core_rolempresa WHERE tenant_id::text = :tid"),
                {"tid": tenant_uuid} if tenant_uuid else {"tid": None},
            )
            .mappings()
            .all()
        )
        related_data["roles"] = [dict(row) for row in roles]

    except Exception as e:
        logger.warning(f"Error recopilando datos relacionados: {e}")
        related_data["error"] = str(e)
        db.rollback()  # Importante: rollback para que la transacción no quede abortada

    # Registrar en audit_log ANTES de borrar
    user_email = current_user.get("email") or current_user.get("sub")
    user_id = current_user.get("user_id")

    # Preparar ids de tenant
    _legacy_id = None
    try:
        _legacy_id = int(tenant_id)
    except Exception:
        _legacy_id = None

    AuditService.log_delete_empresa(
        db=db,
        empresa_data=empresa_data,
        related_data=related_data,
        user_id=user_id,
        user_email=user_email,
        user_role="admin",
        ip_address=None,  # Se puede obtener del request si es necesario
        tenant_uuid=uuid.UUID(tenant_uuid) if tenant_uuid else None,
        tenant_legacy_id=_legacy_id,
    )

    # Ahora sí, borrar en cascada
    try:
        # Desactivar temporalmente el trigger que previene borrar el último admin
        db.execute(text("SET session_replication_role = replica;"))

        # Borrar tenant (cascada automática a muchas tablas por FK)
        if tenant_uuid:
            db.execute(text("DELETE FROM tenants WHERE id::text = :tid"), {"tid": tenant_uuid})

        # Borrar registros restantes manualmente si no tienen FK CASCADE
        db.execute(
            text("DELETE FROM modulos_empresamodulo WHERE tenant_id::text = :tid"),
            {"tid": tenant_uuid},
        )
        db.execute(
            text("DELETE FROM usuarios_usuarioempresa WHERE tenant_id::text = :tid"),
            {"tid": tenant_uuid},
        )

        # Finalmente borrar empresa
        db.execute(text("DELETE FROM core_empresa WHERE id = :eid"), {"eid": tenant_id})

        # Reactivar triggers
        db.execute(text("SET session_replication_role = DEFAULT;"))

        db.commit()

        logger.info(f"✅ Empresa {tenant_id} eliminada completamente con auditoría")

        return {
            "ok": True,
            "tenant_id": tenant_uuid,
            "nombre": empresa_data.get("nombre"),
            "registros_eliminados": {key: len(value) for key, value in related_data.items()},
        }

    except Exception as e:
        # Reactivar triggers antes de hacer rollback
        try:
            db.execute(text("SET session_replication_role = DEFAULT;"))
        except Exception:
            pass
        db.rollback()
        logger.error(f"Error eliminando empresa {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al eliminar empresa: {str(e)}")


class AdminUserIn(BaseModel):
    nombre_encargado: str
    apellido_encargado: str
    email: EmailStr
    username: str
    password: str | None = None


class AdminUserOut(BaseModel):
    id: int
    email: EmailStr
    username: str


class LogoPayload(BaseModel):
    data: str  # base64 (o data URL con prefix)
    filename: str | None = None
    content_type: str | None = None


class EmpresaPayload(BaseModel):
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


class EmpresaCompletaIn(BaseModel):
    empresa: EmpresaPayload
    admin: AdminUserIn
    modulos: list[int] = []
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


@router.post("/completa-json")
async def crear_empresa_completa_json(
    payload: EmpresaCompletaIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Unicidad básica
    if payload.empresa.tax_id:
        exists_ruc = db.query(Empresa).filter(Empresa.tax_id == payload.empresa.tax_id).first()
        if exists_ruc:
            raise HTTPException(status_code=400, detail="empresa_ruc_exists")

    email_clean = (str(payload.admin.email) or "").strip().lower()
    username_clean = (payload.admin.username or "").strip().lower()

    # Autogenera username si no viene: nombre.apellido (normalizado), garantizando unicidad
    if not username_clean:
        try:
            first = slugify(payload.admin.nombre_encargado or "", separator="")
            last = slugify(payload.admin.apellido_encargado or "", separator="")
            base = ".".join([p for p in [first, last] if p]).strip(".")
            if not base:
                base = (email_clean.split("@")[0] or "usuario").strip(".")
            candidate = base.lower()
            # si existe, agrega sufijos incrementales
            i = 1
            while (
                db.query(UsuarioEmpresa)
                .filter(func.lower(UsuarioEmpresa.username) == candidate)
                .first()
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
                db.query(UsuarioEmpresa)
                .filter(
                    (func.lower(UsuarioEmpresa.email) == email_clean)
                    | (func.lower(UsuarioEmpresa.username) == username_clean)
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
        # Empresa (Tenant)
        repo = SqlEmpresaRepo(db)
        empresa_data = payload.empresa.model_dump()
        if not empresa_data.get("slug"):
            empresa_data["slug"] = slugify(empresa_data.get("name") or "")
        created_empresa = repo.create(empresa_data)
        tenant_uuid = created_empresa.get("id")

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
        user = crear_usuario_admin(
            db,
            tenant_id=tenant_uuid,
            nombre_encargado=payload.admin.nombre_encargado,
            apellido_encargado=payload.admin.apellido_encargado,
            email=email_clean,
            username=username_clean,
            password=tmp_password,
        )

        # Módulos
        if tenant_uuid:
            for modulo_id in payload.modulos or []:
                m_in = mod_schemas.EmpresaModuloCreate(modulo_id=modulo_id)
                mod_services.asignar_modulo_a_empresa_si_no_existe(db, tenant_uuid, m_in)

        # AUTO-SETUP (con plantilla de sector opcional)
        if tid:
            try:
                from app.services.tenant_onboarding import auto_setup_tenant

                country = empresa_data.get("pais", "EC")
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
        enviar_correo_bienvenida(user.email, user.username, payload.empresa.name, background_tasks)
    except Exception as e:
        # Do not interrupt the flow on SMTP failure, but log for diagnosis
        logger.warning("Failed to enqueue welcome email for %s: %s", user.email, e, exc_info=True)

    return {"msg": "ok", "id": tenant_uuid}
