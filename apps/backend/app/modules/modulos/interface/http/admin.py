from __future__ import annotations

import json
import os
from pathlib import Path

from apps.backend.app.shared.utils import ping_ok
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.core.module import CompanyModule, Module
from app.modules import crud as mod_crud
from app.modules import schemas as mod_schemas
from app.modules import services as mod_services
from app.modules.modules.interface.http.schemas import ModuloOutSchema

router = APIRouter(
    prefix="/admin/modules",
    tags=["Admin Modules"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


def _module_to_response(m: Module) -> dict:
    """Map Module ORM to response (english only)."""

    return {
        "id": m.id,
        "name": m.name,
        "url": getattr(m, "url", None),
        "icon": getattr(m, "icon", None),
        "category": getattr(m, "category", None),
        "active": m.active,
        "description": getattr(m, "description", None),
        "initial_template": getattr(m, "initial_template", None),
        "context_type": getattr(m, "context_type", None),
        "target_model": getattr(m, "target_model", None),
        "context_filters": getattr(m, "context_filters", None) or {},
    }


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
            "Could not resolve FRONTEND_MODULES_PATH. "
            "Set apps/backend/.env (FRONTEND_MODULES_PATH) to the frontend modules directory "
            "(e.g. apps/tenant/src/modules) and ensure the backend can read it (mount a volume if running in Docker). "
            f"Details: {'; '.join(details)}"
        ),
    )


def _guess_defaults(_slug: str) -> tuple[str | None, str | None]:
    """

    Deprecated fallback. We no longer infer icon/categor├¡a; return (None, None)

    so callers rely on manifest or DB data only.

    """

    return None, None


@router.get("/ping")
def ping_admin_modules():
    return ping_ok()


@router.post(
    "/company/{tenant_id}/users/{user_id}",
    response_model=mod_schemas.ModuloAsignadoOut,
)
def assign_module_to_user(
    tenant_id: int,
    user_id: int,
    module_in: mod_schemas.ModuloAsignadoCreate,
    db: Session = Depends(get_db),
):
    return mod_services.asignar_modulo_a_usuario_si_empresa_lo_tiene(
        db, tenant_id, user_id, module_in.module_id
    )


@router.get(
    "/company/{tenant_id}/users/{user_id}",
    response_model=list[mod_schemas.ModuloAsignadoOut],
)
def list_user_modules(
    tenant_id: int,
    user_id: int,
    db: Session = Depends(get_db),
):
    return mod_crud.obtener_modulos_de_usuario(db, tenant_id, user_id)


@router.get("/", response_model=list[ModuloOutSchema])
def list_admin_modules(db: Session = Depends(get_db)):
    modules = db.query(Module).filter(Module.active).order_by(Module.id.asc()).all()  # noqa: E712

    return [ModuloOutSchema.model_validate(_module_to_response(m)) for m in modules]


@router.get("", response_model=list[ModuloOutSchema])
def list_admin_modules_no_slash(db: Session = Depends(get_db)):
    return list_admin_modules(db)


@router.post("/", response_model=mod_schemas.ModuloOut)
def create_module(module_in: mod_schemas.ModuloCreate, db: Session = Depends(get_db)):
    return mod_crud.crear_modulo(db, module_in)


@router.get("/public", response_model=list[ModuloOutSchema])
def get_public_modules(db: Session = Depends(get_db)):
    """

    Devuelve m├│dulos p├║blicos en formato ligero que espera el panel admin.



    El modelo `Module` usa campos en ingl├®s (`initial_template`, `target_model`, etc.)

    mientras que los schemas legacy esperan nombres en espa├▒ol. Para evitar errors de

    validaci├│n, mapeamos manualmente solo los campos expuestos en `ModuloOutSchema`.

    """

    modules = mod_crud.listar_modules_publicos(db)

    return [ModuloOutSchema.model_validate(_module_to_response(m)) for m in modules]


@router.post("/register-modules")
def register_modules(payload: dict | None = None, db: Session = Depends(get_db)):
    """Register modules from the filesystem.

    Optionally accepts JSON body { "dir": "/path/to/modules" } to force a specific directory during development. If missing, it resolves automatically with _resolve_modules_dir().
    """

    try:
        override_dir = None

        if isinstance(payload, dict):
            override_dir = payload.get("dir")

        # Permitir modo upsert: reactivar y actualizar m├│dulos existentes

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
            "hint": "Set FRONTEND_MODULES_PATH in apps/backend/.env (e.g. apps/tenant/src/modules)",
        }

    # Graceful fallback: evitar 500 si no est├í configurado

    if not modules_dir:
        return {
            "status": "skipped",
            "reason": "FRONTEND_MODULES_PATH not configured",
            "hint": "Define FRONTEND_MODULES_PATH en apps/backend/.env (ruta absoluta, p.ej. C:\\Users\\...\\apps\\tenant\\src\\modules)",
        }

    # Si el path no es v├ílido, evitar 500 y dar pista

    if modules_dir and not os.path.isdir(modules_dir):
        return {
            "status": "skipped",
            "reason": f"Invalid modules_dir: {modules_dir}",
            "hint": "Ensure the backend can access the path (mount a volume in Docker)",
        }

    try:
        carpetas = [
            name
            for name in os.listdir(modules_dir)
            if os.path.isdir(os.path.join(modules_dir, name))
        ]

        registered: list[str] = []

        already_existing: list[str] = []

        reactivated: list[str] = []

        updated: list[str] = []

        ignored: list[str] = []

        errors: list[dict] = []

        for carpeta in carpetas:
            # ignorar carpetas especiales

            if carpeta.startswith(".") or carpeta.startswith("_"):
                ignored.append(carpeta)

                continue

            # Aceptar m├│dulos con Panel.tsx o Routes.tsx para el loader din├ímico

            panel_path = os.path.join(modules_dir, carpeta, "Panel.tsx")

            routes_path = os.path.join(modules_dir, carpeta, "Routes.tsx")

            # Aceptar si existe cualquier archivo .tsx en la carpeta (adem├ís de Panel/Routes)

            if not (
                os.path.exists(panel_path)
                or os.path.exists(routes_path)
                or any(
                    fn.lower().endswith(".tsx")
                    for fn in os.listdir(os.path.join(modules_dir, carpeta))
                )
            ):
                ignored.append(carpeta)

                continue

            name = carpeta.lower()

            existente = db.query(Module).filter_by(name=name).first()

            if existente:
                if reactivate_existing:
                    # Intentar leer manifest (si existe) para actualizar campos b├ísicos

                    manifest_path = os.path.join(modules_dir, carpeta, "module.json")

                    manifest: dict | None = None

                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, encoding="utf-8") as fh:
                                manifest = json.load(fh)

                        except Exception as me:
                            errors.append({"module": name, "error": f"invalid manifest: {me}"})

                    # Defaults v2

                    default_icon, default_cat = _guess_defaults(name)

                    # Deducir una plantilla_inicial si hace falta

                    plantilla_detectada = None

                    try:
                        for _fn in os.listdir(os.path.join(modules_dir, carpeta)):
                            if _fn.lower().endswith(".tsx"):
                                plantilla_detectada = _fn.rsplit(".", 1)[0]

                                break

                    except Exception:
                        pass

                    # Actualizar campos no cr├¡ticos y reactivar

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

                        updated.append(name)

                        reactivated.append(name)

                    except Exception as ue:
                        db.rollback()

                        errors.append({"module": name, "error": f"could not update: {ue}"})

                    continue

                else:
                    already_existing.append(name)

                    continue

            # Intentar leer manifest opcional (module.json)

            manifest_path = os.path.join(modules_dir, carpeta, "module.json")

            manifest: dict | None = None

            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, encoding="utf-8") as fh:
                        manifest = json.load(fh)

                except Exception as me:
                    errors.append({"module": name, "error": f"invalid manifest: {me}"})

            # Construir payload combinando defaults + manifest

            # Use v2 defaults (emoji + categories) when no manifest is present

            default_icon, default_cat = _guess_defaults(name)

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
                "icon": (manifest.get("icon") if manifest else None),
                "active": manifest.get("active", True) if manifest else True,
                "initial_template": (
                    manifest.get("initial_template", plantilla_detectada or name)
                    if manifest
                    else (plantilla_detectada or name)
                ),
                "context_type": manifest.get("context_type", "none") if manifest else "none",
                "context_filters": manifest.get("context_filters", {}) if manifest else {},
                "description": manifest.get("description") if manifest else None,
                "target_model": manifest.get("target_model") if manifest else None,
                "category": manifest.get("category", default_cat) if manifest else default_cat,
            }

            try:
                module = mod_schemas.ModuloCreate(**payload)  # type: ignore[arg-type]

                # Solo crear en BD; no crear archivos/estructura desde detecci├│n FS

                mod_crud.crear_modulo_db_only(db, module)

                registered.append(name)

            except Exception as ce:
                errors.append({"module": name, "error": str(ce)})

        return {
            "registered": registered,
            "already_existing": already_existing,
            "reactivated": reactivated,
            "updated": updated,
            "ignored": ignored,
            "errors": errors,
        }

    except Exception as e:
        db.rollback()

        raise HTTPException(status_code=500, detail=f"Error al registrar m├│dulos: {e}")


@router.post("/company/{tenant_id}", response_model=mod_schemas.EmpresaModuloOut)
def assign_module_to_company(
    tenant_id: str,
    module_in: mod_schemas.EmpresaModuloCreate,
    db: Session = Depends(get_db),
):
    assignment = mod_services.asignar_modulo_a_empresa_si_no_existe(db, tenant_id, module_in)

    db.refresh(assignment)

    _ = assignment.tenant

    _ = assignment.module

    return {
        "id": assignment.id,
        "tenant_id": assignment.tenant_id,
        "company_slug": getattr(assignment.tenant, "slug", None),
        "active": assignment.active,
        "activation_date": getattr(assignment, "activation_date", None),
        "expiration_date": getattr(assignment, "expiration_date", None),
        "initial_template": getattr(assignment, "initial_template", None),
        "module_id": assignment.module_id,
        "module": _module_to_response(assignment.module) if assignment.module else None,
    }


@router.get("/company/{tenant_id}", response_model=list[mod_schemas.EmpresaModuloOut])
def list_company_modules(tenant_id: str, db: Session = Depends(get_db)):
    rows = mod_crud.obtener_modulos_de_empresa(db, tenant_id)

    result = []

    for r in rows:
        module_payload = _module_to_response(r.module) if r.module else None

        result.append(
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "company_slug": r.tenant.slug if r.tenant else None,
                "active": getattr(r, "active", None),
                "activation_date": getattr(r, "activation_date", None),
                "module_id": r.module_id,
                "module": module_payload,
                "expiration_date": getattr(r, "expiration_date", None),
                "initial_template": getattr(r, "initial_template", None),
            }
        )

    return result


@router.post("/company/{tenant_id}/upsert", response_model=mod_schemas.EmpresaModuloOutAdmin)
def upsert_company_module(
    tenant_id: str,
    module_in: mod_schemas.EmpresaModuloCreate,
    db: Session = Depends(get_db),
):
    return mod_services.upsert_modulo_a_empresa(db, tenant_id, module_in)


@router.delete("/company/{tenant_id}/module/{module_id}")
def delete_company_module(tenant_id: str, module_id: str, db: Session = Depends(get_db)):
    company_module = (
        db.query(CompanyModule).filter_by(tenant_id=tenant_id, module_id=module_id).first()
    )

    if not company_module:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(company_module)

    db.commit()

    return {"ok": True}
