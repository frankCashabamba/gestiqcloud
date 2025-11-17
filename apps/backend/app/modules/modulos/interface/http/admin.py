from __future__ import annotations

import json
import os
from pathlib import Path

from app.config.database import get_db
from app.config.settings import settings
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.core.modulo import EmpresaModulo, Modulo
from app.modules import crud as mod_crud
from app.modules import schemas as mod_schemas
from app.modules import services as mod_services
from app.modules.modulos.application.use_cases import ListarModulosAdmin
from app.modules.modulos.infrastructure.repositories import SqlModuloRepo
from app.modules.modulos.interface.http.schemas import ModuloOutSchema
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.backend.app.shared.utils import ping_ok

router = APIRouter(
    prefix="/admin/modulos",
    tags=["Admin Modulos"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


def _resolve_modules_dir() -> str:
    """Resolve a readable frontend modules directory in dev/compose.

    Preference:
    1) Use FRONTEND_MODULES_PATH if it exists.
    2) If not, try to find repo root (folder containing 'apps') relative to this file,
       and probe common locations like apps/tenant/src/modules and apps/src/modules.
    3) If still missing, raise with guidance.
    """
    cfg = settings.FRONTEND_MODULES_PATH
    if cfg and os.path.isdir(cfg):
        return cfg

    here = Path(__file__).resolve()
    repo_root: Path | None = None
    for parent in here.parents:
        if (parent / "apps").is_dir():
            repo_root = parent
            break

    candidates: list[Path] = []
    if cfg and repo_root is not None:
        rel = cfg.lstrip("/\\")
        candidates.append(repo_root / rel)
    if repo_root is not None:
        candidates.extend(
            [
                repo_root / "apps" / "tenant" / "src" / "modules",
                repo_root / "apps" / "src" / "modules",
            ]
        )

    for c in candidates:
        if c.is_dir():
            return str(c)

    details = [
        f"cfg={cfg!r}",
        f"repo_root={(str(repo_root) if repo_root else 'not-found')}",
    ]
    raise HTTPException(
        status_code=500,
        detail=(
            "No se pudo resolver FRONTEND_MODULES_PATH. "
            "Configura apps/backend/.env (FRONTEND_MODULES_PATH) al directorio de módulos del frontend "
            "(p.ej. apps/tenant/src/modules) y asegúrate que el backend tenga acceso (monta un volumen en compose si corre en contenedor). "
            f"Detalles: {'; '.join(details)}"
        ),
    )


def _guess_defaults_v2(slug: str) -> tuple[str | None, str | None]:
    """Infer default icon and category for well-known module slugs.

    Defaults:
    - ventas/compras/facturacion -> icon: 🧾, categoría: operaciones
    - inventario -> icon: 📦, categoría: operaciones
    - rrhh -> icon: 👤, categoría: operaciones
    - importador -> icon: None, categoría: herramientas

    For other slugs, leave both as None to allow manual edit.
    """
    s = slug.lower()
    icon_map: dict[str, str | None] = {
        "ventas": "🧾",
        "compras": "🧾",
        "facturacion": "🧾",
        "inventario": "📦",
        "rrhh": "👤",
        "imports": "📥",
    }
    cat_map: dict[str, str | None] = {
        "ventas": "operaciones",
        "compras": "operaciones",
        "facturacion": "operaciones",
        "inventario": "operaciones",
        "rrhh": "operaciones",
        "imports": "tools",
    }
    return icon_map.get(s), cat_map.get(s)


def _guess_defaults(slug: str) -> tuple[str, str | None]:
    """Infer icon and category from common slug names when no manifest is present."""
    s = slug.lower()
    icon_map = {
        "sales": "🧾",
        "purchases": "🧾",
        "invoicing": "🧾",
        "inventory": "📦",
        "accounting": "📒",
        "finance": "💳",
        "suppliers": "🏷️",
        "clients": "👥",
        "hr": "👤",
        "imports": "📥",
        "settings": "⚙️",
    }
    cat_map = {
        "sales": "operations",
        "purchases": "operations",
        "invoicing": "operations",
        "inventory": "operations",
        "accounting": "finance",
        "finance": "finance",
        "suppliers": "masters",
        "clients": "masters",
        "hr": "operations",
        "imports": "tools",
        "settings": "configuration",
    }
    return icon_map.get(s, "📦"), cat_map.get(s)


@router.get("/ping")
def ping_admin_modulos():
    return ping_ok()


@router.post(
    "/empresa/{tenant_id}/usuarios/{usuario_id}",
    response_model=mod_schemas.ModuloAsignadoOut,
)
def asignar_modulo_a_usuario(
    tenant_id: int,
    usuario_id: int,
    modulo_in: mod_schemas.ModuloAsignadoCreate,
    db: Session = Depends(get_db),
):
    return mod_services.asignar_modulo_a_usuario_si_empresa_lo_tiene(
        db, tenant_id, usuario_id, modulo_in.modulo_id
    )


@router.get(
    "/empresa/{tenant_id}/usuarios/{usuario_id}",
    response_model=list[mod_schemas.ModuloAsignadoOut],
)
def listar_modulos_de_usuario(
    tenant_id: int,
    usuario_id: int,
    db: Session = Depends(get_db),
):
    return mod_crud.obtener_modulos_de_usuario(db, tenant_id, usuario_id)


@router.get("/", response_model=list[ModuloOutSchema])
def listar_modulos_admin(db: Session = Depends(get_db)):
    use = ListarModulosAdmin(SqlModuloRepo(db))
    items = use.execute()
    return [ModuloOutSchema.model_construct(**i) for i in items]


# Evitar redirección 307 por barra final: expone también la ruta sin barra
@router.get("", response_model=list[ModuloOutSchema])
def listar_modulos_admin_no_slash(db: Session = Depends(get_db)):
    return listar_modulos_admin(db)


@router.post("/", response_model=mod_schemas.ModuloOut)
def crear_modulo(modulo_in: mod_schemas.ModuloCreate, db: Session = Depends(get_db)):
    return mod_crud.crear_modulo(db, modulo_in)


@router.get("/publicos", response_model=list[mod_schemas.ModuloOut])
def obtener_modulos_publicos(db: Session = Depends(get_db)):
    return mod_crud.listar_modulos_publicos(db)


@router.post("/registrar-modulos")
def registrar_modulos(payload: dict | None = None, db: Session = Depends(get_db)):
    """Registra módulos a partir del filesystem.

    Opcionalmente acepta body JSON { "dir": "/ruta/a/modules" } para forzar
    un directorio específico durante desarrollo. Si no se pasa, intenta
    resolverlo automáticamente con _resolve_modules_dir().
    """
    try:
        override_dir = None
        if isinstance(payload, dict):
            override_dir = payload.get("dir")
        # Permitir modo upsert: reactivar y actualizar módulos existentes
        reactivate_existing = False
        if isinstance(payload, dict):
            reactivate_existing = bool(
                payload.get("reactivar_si_existe")
                or payload.get("upsert")
                or payload.get("reactivar")
            )
        modules_dir = override_dir or _resolve_modules_dir()
    except HTTPException as e:
        return {
            "status": "skipped",
            "reason": str(e.detail),
            "hint": "Define FRONTEND_MODULES_PATH en apps/backend/.env (p.ej. apps/tenant/src/modules)",
        }
    # Graceful fallback: evitar 500 si no está configurado
    if not modules_dir:
        return {
            "status": "skipped",
            "reason": "FRONTEND_MODULES_PATH not configured",
            "hint": "Define FRONTEND_MODULES_PATH en apps/backend/.env (p.ej. apps/tenant/src/modules)",
        }
    if not modules_dir:
        raise HTTPException(
            status_code=500,
            detail="FRONTEND_MODULES_PATH no está configurado en el backend",
        )
    # Si el path no es válido, evitar 500 y dar pista
    if modules_dir and not os.path.isdir(modules_dir):
        return {
            "status": "skipped",
            "reason": f"Invalid modules_dir: {modules_dir}",
            "hint": "Asegura que el backend tiene acceso al path (monta volumen en Docker)",
        }
    try:
        carpetas = [
            name
            for name in os.listdir(modules_dir)
            if os.path.isdir(os.path.join(modules_dir, name))
        ]
        registrados: list[str] = []
        ya_existentes: list[str] = []
        reactivados: list[str] = []
        actualizados: list[str] = []
        ignorados: list[str] = []
        errores: list[dict] = []
        for carpeta in carpetas:
            # ignorar carpetas especiales
            if carpeta.startswith(".") or carpeta.startswith("_"):
                ignorados.append(carpeta)
                continue
            # Aceptar módulos con Panel.tsx o Routes.tsx para el loader dinámico
            panel_path = os.path.join(modules_dir, carpeta, "Panel.tsx")
            routes_path = os.path.join(modules_dir, carpeta, "Routes.tsx")
            # Aceptar si existe cualquier archivo .tsx en la carpeta (además de Panel/Routes)
            if not (
                os.path.exists(panel_path)
                or os.path.exists(routes_path)
                or any(
                    fn.lower().endswith(".tsx")
                    for fn in os.listdir(os.path.join(modules_dir, carpeta))
                )
            ):
                ignorados.append(carpeta)
                continue
            name = carpeta.lower()
            existente = db.query(Modulo).filter_by(name=name).first()
            if existente:
                if reactivate_existing:
                    # Intentar leer manifest (si existe) para actualizar campos básicos
                    manifest_path = os.path.join(modules_dir, carpeta, "module.json")
                    manifest: dict | None = None
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, encoding="utf-8") as fh:
                                manifest = json.load(fh)
                        except Exception as me:
                            errores.append({"modulo": name, "error": f"manifest invalido: {me}"})
                    # Defaults v2
                    default_icon, default_cat = _guess_defaults_v2(name)
                    # Deducir una plantilla_inicial si hace falta
                    plantilla_detectada = None
                    try:
                        for _fn in os.listdir(os.path.join(modules_dir, carpeta)):
                            if _fn.lower().endswith(".tsx"):
                                plantilla_detectada = _fn.rsplit(".", 1)[0]
                                break
                    except Exception:
                        pass
                    # Actualizar campos no críticos y reactivar
                    try:
                        if manifest and manifest.get("url"):
                            existente.url = manifest.get("url")  # type: ignore[assignment]
                        elif not existente.url:
                            existente.url = name  # type: ignore[assignment]
                        if manifest and manifest.get("icono") is not None:
                            existente.icono = manifest.get("icono")  # type: ignore[assignment]
                        elif not existente.icono and default_icon is not None:
                            existente.icono = default_icon  # type: ignore[assignment]
                        if manifest and manifest.get("categoria") is not None:
                            existente.categoria = manifest.get("categoria")  # type: ignore[assignment]
                        elif not existente.categoria and default_cat is not None:
                            existente.categoria = default_cat  # type: ignore[assignment]
                        if (
                            not getattr(existente, "plantilla_inicial", None)
                            and plantilla_detectada
                        ):
                            existente.plantilla_inicial = plantilla_detectada  # type: ignore[assignment]
                        existente.active = True  # type: ignore[assignment]
                        db.add(existente)
                        db.commit()
                        actualizados.append(name)
                        reactivados.append(name)
                    except Exception as ue:
                        db.rollback()
                        errores.append({"modulo": name, "error": f"no se pudo actualizar: {ue}"})
                    continue
                else:
                    ya_existentes.append(name)
                    continue
            # Intentar leer manifest opcional (module.json)
            manifest_path = os.path.join(modules_dir, carpeta, "module.json")
            manifest: dict | None = None
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, encoding="utf-8") as fh:
                        manifest = json.load(fh)
                except Exception as me:
                    errores.append({"modulo": name, "error": f"manifest invalido: {me}"})
            # Construir payload combinando defaults + manifest
            # Use v2 defaults (emoji + categories) when no manifest is present
            default_icon, default_cat = _guess_defaults_v2(name)
            # Si no hay manifest, intente usar como plantilla el primer .tsx encontrado
            plantilla_detectada = None
            try:
                for _fn in os.listdir(os.path.join(modules_dir, carpeta)):
                    if _fn.lower().endswith(".tsx"):
                        plantilla_detectada = _fn.rsplit(".", 1)[0]
                        break
            except Exception:
                pass
            payload = {
                "name": name,
                "url": (manifest.get("url") if manifest else name) or name,
                "icono": (manifest.get("icono") if manifest else None),
                # Mantener compatibilidad con manifests antiguos (activo) y nuevos (active)
                "active": (
                    manifest.get("active", manifest.get("activo", True)) if manifest else True
                ),
                "plantilla_inicial": (
                    manifest.get("plantilla_inicial", plantilla_detectada or name)
                    if manifest
                    else (plantilla_detectada or name)
                ),
                "context_type": manifest.get("context_type", "none") if manifest else "none",
                "filtros_contexto": manifest.get("filtros_contexto", {}) if manifest else {},
                "descripcion": manifest.get("descripcion") if manifest else None,
                "modelo_objetivo": manifest.get("modelo_objetivo") if manifest else None,
                "categoria": manifest.get("categoria", default_cat) if manifest else default_cat,
            }
            try:
                modulo = mod_schemas.ModuloCreate(**payload)  # type: ignore[arg-type]
                # Solo crear en BD; no crear archivos/estructura desde detección FS
                mod_crud.crear_modulo_db_only(db, modulo)
                registrados.append(name)
            except Exception as ce:
                errores.append({"modulo": name, "error": str(ce)})
        return {
            "registrados": registrados,
            "ya_existentes": ya_existentes,
            "reactivados": reactivados,
            "actualizados": actualizados,
            "ignorados": ignorados,
            "errores": errores,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar módulos: {e}")


@router.post("/empresa/{tenant_id}", response_model=mod_schemas.EmpresaModuloOut)
def asignar_modulo_a_empresa(
    tenant_id: int,
    modulo_in: mod_schemas.EmpresaModuloCreate,
    db: Session = Depends(get_db),
):
    return mod_services.asignar_modulo_a_empresa_si_no_existe(db, tenant_id, modulo_in)


@router.get("/empresa/{tenant_id}", response_model=list[mod_schemas.EmpresaModuloOut])
def listar_modulos_de_empresa(tenant_id: str, db: Session = Depends(get_db)):
    registros = mod_crud.obtener_modulos_de_empresa(db, tenant_id)
    resultado = []
    for r in registros:
        resultado.append(
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "empresa_slug": r.tenant.slug if r.tenant else None,
                "active": r.activo,
                "fecha_activacion": r.fecha_activacion,
                "modulo_id": r.modulo_id,
                "modulo": r.modulo,
                "fecha_expiracion": r.fecha_expiracion,
            }
        )
    return resultado


@router.post("/empresa/{tenant_id}/upsert", response_model=mod_schemas.EmpresaModuloOutAdmin)
def upsert_modulo_empresa(
    tenant_id: str,
    modulo_in: mod_schemas.EmpresaModuloCreate,
    db: Session = Depends(get_db),
):
    return mod_services.upsert_modulo_a_empresa(db, tenant_id, modulo_in)


@router.delete("/empresa/{tenant_id}/modulo/{modulo_id}")
def eliminar_modulo_de_empresa(tenant_id: str, modulo_id: int, db: Session = Depends(get_db)):
    empresa_modulo = (
        db.query(EmpresaModulo).filter_by(tenant_id=tenant_id, modulo_id=modulo_id).first()
    )
    if not empresa_modulo:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    db.delete(empresa_modulo)
    db.commit()
    return {"ok": True}
