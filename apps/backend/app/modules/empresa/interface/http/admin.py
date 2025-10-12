from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.modules.empresa.application.use_cases import ListarEmpresasAdmin, crear_usuario_admin
from app.db.rls import set_tenant_guc
from app.modules.empresa.infrastructure.repositories import SqlEmpresaRepo
from app.modules.empresa.interface.http.schemas import EmpresaInSchema, EmpresaOutSchema
from app.models.empresa.empresa import Empresa
from app.models.empresa.usuarioempresa import UsuarioEmpresa
from pydantic import BaseModel, EmailStr
from pathlib import Path
import os
import uuid
from slugify import slugify
from typing import List
from app.modules import services as mod_services, schemas as mod_schemas, crud as mod_crud
from app.api.email.email_utils import enviar_correo_bienvenida


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
        empresa_id = int(i.get("id")) if i.get("id") is not None else None
        mod_names: list[str] = []
        if empresa_id is not None:
            try:
                registros = mod_crud.obtener_modulos_de_empresa(db, empresa_id)
                mod_names = [getattr(r.modulo, "nombre", None) for r in registros if getattr(r, "modulo", None)]
            except Exception:
                mod_names = []
        enriched = {**i, "modulos": mod_names}
        out.append(EmpresaOutSchema.model_validate(enriched))
    return out


@router.get("/{empresa_id}", response_model=EmpresaOutSchema)
def obtener_empresa_admin(empresa_id: int, db: Session = Depends(get_db)) -> EmpresaOutSchema:
    repo = SqlEmpresaRepo(db)
    item = repo.get(id=empresa_id)
    if not item:
        raise HTTPException(status_code=404, detail="empresa_not_found")
    # Enriquecer con modulos como en el listado
    try:
        registros = mod_crud.obtener_modulos_de_empresa(db, empresa_id)
        mod_names = [getattr(r.modulo, "nombre", None) for r in registros if getattr(r, "modulo", None)]
    except Exception:
        mod_names = []
    enriched = {**item, "modulos": mod_names}
    return EmpresaOutSchema.model_validate(enriched)


@router.put("/{empresa_id}", response_model=EmpresaOutSchema)
def actualizar_empresa(empresa_id: int, payload: EmpresaInSchema, db: Session = Depends(get_db)):
    repo = SqlEmpresaRepo(db)
    updated = repo.update(empresa_id, payload.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="empresa_not_found")
    return EmpresaOutSchema.model_construct(**updated)


@router.delete("/{empresa_id}")
def eliminar_empresa(empresa_id: int, db: Session = Depends(get_db)):
    repo = SqlEmpresaRepo(db)
    ok = repo.delete(empresa_id)
    if not ok:
        raise HTTPException(status_code=404, detail="empresa_not_found")
    return {"ok": True}


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
    nombre: str
    slug: str | None = None
    ruc: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    provincia: str | None = None
    cp: str | None = None
    pais: str | None = None
    logo: str | None = None
    color_primario: str | None = None
    activo: bool | None = True
    motivo_desactivacion: str | None = None
    plantilla_inicio: str | None = "cliente"
    sitio_web: str | None = None
    config_json: dict | None = None


class EmpresaCompletaIn(BaseModel):
    empresa: EmpresaPayload
    admin: AdminUserIn
    modulos: list[int] = []
    logo: LogoPayload | None = None


def _decode_data_url(data: str) -> tuple[bytes, str | None]:
    import base64, re
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
    if payload.empresa.ruc:
        exists_ruc = db.query(Empresa).filter(Empresa.ruc == payload.empresa.ruc).first()
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
            while db.query(UsuarioEmpresa).filter(func.lower(UsuarioEmpresa.username) == candidate).first():
                i += 1
                candidate = f"{base}{i}".lower()
            username_clean = candidate
        except Exception:
            # fallback mínimo
            username_clean = (email_clean.split("@")[0] or "usuario").lower()

    # Verificación de unicidad email/username definitivos
    if email_clean or username_clean:
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

    try:
        # Empresa
        repo = SqlEmpresaRepo(db)
        empresa_data = payload.empresa.model_dump()
        if not empresa_data.get("slug"):
            empresa_data["slug"] = slugify(empresa_data.get("nombre") or "")
        created = repo.create(empresa_data)
        # created es EmpresaDTO (dict-like), usar acceso por clave
        empresa_id = int(created.get("id"))

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
            repo.update(empresa_id, {"logo": f"/uploads/logos/{fname}"})

        # Auto-asignación de tenant + plantilla y fijar contexto RLS ANTES de crear usuario
        try:
            # Asegura fila en tenants (empresa_id único)
            db.execute(
                text(
                    "INSERT INTO tenants(empresa_id, slug) VALUES (:eid, :slug) ON CONFLICT (empresa_id) DO NOTHING"
                ),
                {"eid": empresa_id, "slug": empresa_data.get("slug")},
            )
            # Obtiene tenant_id UUID
            tid = db.execute(text("SELECT id::text FROM tenants WHERE empresa_id=:eid"), {"eid": empresa_id}).scalar()
            if tid:
                # Fija GUC en esta sesión/transacción para que DEFAULTs/Policies apliquen
                set_tenant_guc(db, tid, persist=False)
            # Clave de paquete por env
            tpl_key = os.getenv("DEFAULT_TENANT_TEMPLATE_KEY", "bazar").strip() or "bazar"
            ver = db.execute(
                text("SELECT version FROM template_packages WHERE template_key=:k ORDER BY version DESC LIMIT 1"),
                {"k": tpl_key},
            ).scalar()
            if tid and ver:
                db.execute(
                    text(
                        """
                        INSERT INTO tenant_templates(tenant_id, template_key, version, active)
                        VALUES (CAST(:tid AS uuid), :k, :ver, true)
                        ON CONFLICT (tenant_id, template_key) DO UPDATE SET version=EXCLUDED.version, active=true
                        """
                    ),
                    {"tid": tid, "k": tpl_key, "ver": int(ver)},
                )
        except Exception:
            # No interrumpir la creación si falla auto-asignación
            tid = None
            pass

        # Usuario admin (contraseña opcional) — requiere tenant GUC activo o asignación explícita
        import secrets
        tmp_password = payload.admin.password or secrets.token_urlsafe(24)
        user = crear_usuario_admin(
            db,
            empresa_id=empresa_id,
            nombre_encargado=payload.admin.nombre_encargado,
            apellido_encargado=payload.admin.apellido_encargado,
            email=email_clean,
            username=username_clean,
            password=tmp_password,
        )
        # En caso de que el ORM vaya a enviar tenant_id NULL, fuerza el valor correcto
        try:
            if tid and getattr(user, "tenant_id", None) in (None, ""):
                user.tenant_id = tid
        except Exception:
            pass

        # Módulos
        for modulo_id in payload.modulos or []:
            m_in = mod_schemas.EmpresaModuloCreate(modulo_id=modulo_id)
            mod_services.asignar_modulo_a_empresa_si_no_existe(db, empresa_id, m_in)

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    try:
        enviar_correo_bienvenida(user.email, user.username, payload.empresa.nombre, background_tasks)
    except Exception as e:
        # Do not interrupt the flow on SMTP failure, but log for diagnosis
        logger.warning("Failed to enqueue welcome email for %s: %s", user.email, e, exc_info=True)

    return {"msg": "ok", "id": empresa_id}
