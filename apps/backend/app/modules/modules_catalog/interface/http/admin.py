from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from apps.backend.app.shared.utils import ping_ok
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.core.module import CompanyModule, Module
from app.modules import crud as mod_crud
from app.modules import schemas as mod_schemas
from app.modules import services as mod_services
from app.modules.modules_catalog.interface.http.schemas import ModuloOutSchema
from app.modules.settings.application.modules_catalog import (
    canonicalize_module_id,
    get_available_modules,
    get_module_aliases,
)

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


def _normalize_module_name(folder_name: str) -> str:
    """Normalize Spanish/other folder names to English.

    This ensures all modules are registered with English names,
    allowing the frontend to handle translations via i18n.
    """
    mapping = {
        "compras": "purchases",
        "ventas": "sales",
        "facturacion": "billing",
        "facturación": "billing",
        "reportes": "reports",
        "usuarios": "users",
        "produccion": "manufacturing",
        "producción": "manufacturing",
        "clientes": "customers",
        "proveedores": "suppliers",
        "inventario": "inventory",
        "gastos": "expenses",
        "finanzas": "finances",
        "contabilidad": "accounting",
    }

    normalized = folder_name.lower()
    return mapping.get(normalized, normalized)


def _guess_defaults(_slug: str) -> tuple[str | None, str | None]:
    """

    Deprecated fallback. We no longer infer icon/categor├¡a; return (None, None)

    so callers rely on manifest or DB data only.

    """

    return None, None


def _load_module_manifest(manifest_path: Path, module_name: str, errors: list[dict]) -> dict | None:
    if not manifest_path.is_file():
        return None

    try:
        with manifest_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        errors.append({"module": module_name, "error": f"invalid manifest: {exc}"})
        return None

    if isinstance(data, dict):
        return data

    errors.append({"module": module_name, "error": "invalid manifest: expected object"})
    return None


def _manifest_value(manifest: dict | None, *keys: str, default=None):
    if not manifest:
        return default

    for key in keys:
        if key in manifest and manifest[key] is not None:
            return manifest[key]

    return default


def _detect_initial_template(panel_path: Path, routes_path: Path, fallback: str) -> str:
    if panel_path.exists():
        return "Panel"
    if routes_path.exists():
        return "Routes"
    return fallback


def _build_module_payload(
    name: str,
    *,
    manifest: dict | None,
    initial_template: str,
    default_icon: str | None = None,
    default_category: str | None = None,
) -> dict:
    catalog_id = _manifest_value(manifest, "id", default=name) or name
    return {
        "name": name,
        "url": _manifest_value(manifest, "url", default=catalog_id) or catalog_id,
        "icon": _manifest_value(manifest, "icon", "icono", default=default_icon),
        "active": bool(_manifest_value(manifest, "active", "activo", default=True)),
        "initial_template": (
            _manifest_value(
                manifest,
                "initial_template",
                "plantilla_inicial",
                default=initial_template,
            )
            or initial_template
        ),
        "context_type": _manifest_value(manifest, "context_type", default="none") or "none",
        "context_filters": _manifest_value(
            manifest, "context_filters", "filtros_contexto", default={}
        )
        or {},
        "description": _manifest_value(manifest, "description", "descripcion"),
        "target_model": _manifest_value(manifest, "target_model", "modelo_objetivo"),
        "category": _manifest_value(
            manifest,
            "category",
            "categoria",
            default=default_category,
        ),
        "implemented": bool(_manifest_value(manifest, "implemented", default=True)),
        "required": bool(_manifest_value(manifest, "required", default=False)),
        "default_enabled": bool(_manifest_value(manifest, "default_enabled", default=True)),
        "dependencies": _manifest_value(manifest, "dependencies", default=[]) or [],
        "aliases": _manifest_value(manifest, "aliases", default=[]) or [],
        "countries": _manifest_value(manifest, "countries", default=["ES", "EC"]) or ["ES", "EC"],
        "sectors": _manifest_value(manifest, "sectors", default=None),
    }


def _merge_catalog_context_filters(
    payload: dict,
    *,
    existing: Module | None = None,
    canonical_name: str | None = None,
) -> dict:
    current = getattr(existing, "context_filters", None) or {}
    incoming = payload.get("context_filters") or {}
    merged = {**current, **incoming}

    catalog_id = (
        current.get("catalog_id")
        or canonicalize_module_id(payload.get("url"))
        or canonicalize_module_id(payload.get("name"))
        or canonicalize_module_id(getattr(existing, "url", None) if existing else None)
        or canonicalize_module_id(getattr(existing, "name", None) if existing else None)
        or canonicalize_module_id(canonical_name)
    )
    if catalog_id:
        merged["catalog_id"] = catalog_id

    return merged


def _collect_filesystem_module_entries(
    modules_dir: str,
) -> tuple[list[dict], list[str], list[dict]]:
    entries: list[dict] = []
    ignored: list[str] = []
    errors: list[dict] = []

    for module_dir in sorted(Path(modules_dir).iterdir()):
        if not module_dir.is_dir():
            continue

        folder_name = module_dir.name
        if folder_name.startswith(".") or folder_name.startswith("_"):
            ignored.append(folder_name)
            continue

        panel_path = module_dir / "Panel.tsx"
        routes_path = module_dir / "Routes.tsx"
        if not (panel_path.exists() or routes_path.exists()):
            ignored.append(folder_name)
            continue

        name = _normalize_module_name(folder_name)
        manifest = _load_module_manifest(module_dir / "module.json", name, errors)
        default_icon, default_category = _guess_defaults(name)
        initial_template = _detect_initial_template(panel_path, routes_path, name)
        payload = _build_module_payload(
            name,
            manifest=manifest,
            initial_template=initial_template,
            default_icon=default_icon,
            default_category=default_category,
        )
        entries.append({"name": name, "payload": payload})

    return entries, ignored, errors


def _collect_catalog_module_entries(db: Session | None = None) -> tuple[list[dict], list[str], list[dict]]:
    entries: list[dict] = []
    ignored: list[str] = []
    seen: set[str] = set()

    for item in get_available_modules(db=db):
        raw_id = str(item.get("id") or "").strip()
        if not raw_id:
            ignored.append(str(item))
            continue

        name = _normalize_module_name(raw_id)
        if name in seen:
            continue
        seen.add(name)

        payload = {
            "name": name,
            "url": raw_id,
            "icon": item.get("icon"),
            "active": True,
            "initial_template": name,
            "context_type": "none",
            "context_filters": {"catalog_id": name},
            "description": item.get("description"),
            "target_model": None,
            "category": item.get("category"),
        }
        entries.append({"name": name, "payload": payload})

    return entries, ignored, []


def _update_existing_module(existing: Module, payload: dict) -> None:
    existing.url = payload.get("url") or existing.url or payload["name"]  # type: ignore[assignment]

    if payload.get("icon") is not None:
        existing.icon = payload.get("icon")  # type: ignore[assignment]
    if payload.get("category") is not None:
        existing.category = payload.get("category")  # type: ignore[assignment]
    if payload.get("description") is not None:
        existing.description = payload.get("description")  # type: ignore[assignment]
    if payload.get("initial_template"):
        existing.initial_template = payload["initial_template"]  # type: ignore[assignment]
    if payload.get("context_type"):
        existing.context_type = payload["context_type"]  # type: ignore[assignment]
    if payload.get("target_model") is not None:
        existing.target_model = payload.get("target_model")  # type: ignore[assignment]
    if payload.get("context_filters") is not None:
        existing.context_filters = payload.get("context_filters") or {}  # type: ignore[assignment]

    existing.active = bool(payload.get("active", True))  # type: ignore[assignment]


def _normalize_module_name(folder_name: str) -> str:
    canonical = canonicalize_module_id(folder_name)
    if canonical:
        return canonical
    return folder_name.strip().lower()


def _find_existing_module(db: Session, canonical_name: str) -> Module | None:
    aliases = [alias.lower() for alias in get_module_aliases(canonical_name)]
    rows = db.query(Module).filter(func.lower(Module.name).in_(aliases)).all()
    if not rows:
        return None
    for row in rows:
        if str(getattr(row, "name", "")).strip().lower() == canonical_name:
            return row
    return rows[0]


def _module_payload_needs_sync(existing: Module, payload: dict, *, sync_active: bool) -> bool:
    expected_url = payload.get("url") or existing.url or payload["name"]
    if getattr(existing, "url", None) != expected_url:
        return True

    comparable_fields = (
        "icon",
        "category",
        "description",
        "initial_template",
        "context_type",
        "target_model",
    )
    for field in comparable_fields:
        incoming = payload.get(field)
        if incoming is not None and getattr(existing, field, None) != incoming:
            return True

    current_filters = getattr(existing, "context_filters", None) or {}
    incoming_filters = _merge_catalog_context_filters(payload, existing=existing)
    if incoming_filters is not None and current_filters != (incoming_filters or {}):
        return True

    if sync_active and bool(getattr(existing, "active", True)) != bool(payload.get("active", True)):
        return True

    current_name = str(getattr(existing, "name", "")).strip().lower()
    canonical_name = str(payload.get("name", "")).strip().lower()
    if canonical_name and current_name != canonical_name:
        return True

    return False


def _update_existing_module(
    existing: Module,
    payload: dict,
    *,
    sync_active: bool = True,
    sync_name: bool = True,
) -> None:
    merged_filters = _merge_catalog_context_filters(
        payload,
        existing=existing,
        canonical_name=payload["name"],
    )
    catalog_id = merged_filters.get("catalog_id")

    if catalog_id:
        existing.url = catalog_id  # type: ignore[assignment]
    else:
        existing.url = payload.get("url") or existing.url or payload["name"]  # type: ignore[assignment]

    if sync_name:
        existing.name = payload.get("name") or existing.name  # type: ignore[assignment]

    if payload.get("icon") is not None:
        existing.icon = payload.get("icon")  # type: ignore[assignment]
    if payload.get("category") is not None:
        existing.category = payload.get("category")  # type: ignore[assignment]
    if payload.get("description") is not None:
        existing.description = payload.get("description")  # type: ignore[assignment]
    if payload.get("initial_template"):
        existing.initial_template = payload["initial_template"]  # type: ignore[assignment]
    if payload.get("context_type"):
        existing.context_type = payload["context_type"]  # type: ignore[assignment]
    if payload.get("target_model") is not None:
        existing.target_model = payload.get("target_model")  # type: ignore[assignment]
    existing.context_filters = merged_filters  # type: ignore[assignment]

    if sync_active:
        existing.active = bool(payload.get("active", True))  # type: ignore[assignment]


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
    payload = module_in.model_dump()
    payload["context_filters"] = _merge_catalog_context_filters(
        payload,
        canonical_name=payload.get("name"),
    )
    module_in = mod_schemas.ModuloCreate(**payload)
    return mod_crud.crear_modulo(db, module_in)


@router.get("/public", response_model=list[ModuloOutSchema])
def get_public_modules(db: Session = Depends(get_db)):
    """

    Devuelve m├│dulos p├║blicos en formato ligero que espera el panel admin.



    El modelo `Module` usa campos en ingl├®s (`initial_template`, `target_model`, etc.)

    mientras que los schemas legacy esperan nombres en espa├▒ol. Para evitar errors de

    validaci├│n, mapeamos manualmente solo los campos expuestos en `ModuloOutSchema`.

    """

    modules = mod_crud.list_public_modules(db)

    return [ModuloOutSchema.model_validate(_module_to_response(m)) for m in modules]


@router.post("/register-modules")
def register_modules(payload: dict | None = None, db: Session = Depends(get_db)):
    """Register modules from the frontend filesystem or backend catalog.

    If a readable frontend modules directory is available, it is used as the source of truth.
    Otherwise, the endpoint falls back to the backend catalog so split deployments
    (backend on VPS, frontend elsewhere) can still register modules.
    """

    override_dir = payload.get("dir") if isinstance(payload, dict) else None
    reactivate_existing = False
    if isinstance(payload, dict):
        reactivate_existing = bool(
            payload.get("reactivar_si_existe") or payload.get("upsert") or payload.get("reactivar")
        )

    source = "filesystem"
    warnings: list[str] = []
    modules_dir: str | None = None

    if override_dir:
        if os.path.isdir(override_dir):
            modules_dir = override_dir
        else:
            warnings.append(
                "Override modules_dir is not readable; falling back to backend catalog."
            )
    else:
        try:
            modules_dir = _resolve_modules_dir()
        except HTTPException as exc:
            warnings.append(str(exc.detail))

    if modules_dir and os.path.isdir(modules_dir):
        entries, ignored, errors = _collect_filesystem_module_entries(modules_dir)
    else:
        source = "backend_catalog"
        entries, ignored, errors = _collect_catalog_module_entries(db)

    registered: list[str] = []
    already_existing: list[str] = []
    reactivated: list[str] = []
    updated: list[str] = []

    try:
        for entry in entries:
            name = entry["name"]
            module_payload = entry["payload"]
            existing = _find_existing_module(db, name)
            module_payload["context_filters"] = _merge_catalog_context_filters(
                module_payload,
                existing=existing,
                canonical_name=name,
            )

            if existing:
                try:
                    needs_sync = _module_payload_needs_sync(
                        existing,
                        module_payload,
                        sync_active=reactivate_existing,
                    )

                    if not needs_sync:
                        already_existing.append(name)
                        continue

                    was_inactive = not bool(getattr(existing, "active", True))
                    _update_existing_module(
                        existing,
                        module_payload,
                        sync_active=reactivate_existing,
                        sync_name=reactivate_existing,
                    )
                    db.add(existing)
                    db.commit()
                    updated.append(name)
                    if (
                        reactivate_existing
                        and was_inactive
                        and bool(getattr(existing, "active", True))
                    ):
                        reactivated.append(name)
                except Exception as exc:
                    db.rollback()
                    errors.append({"module": name, "error": f"could not update: {exc}"})
                continue

            try:
                module = mod_schemas.ModuloCreate(**module_payload)  # type: ignore[arg-type]
                mod_crud.crear_modulo_db_only(db, module)
                registered.append(name)
            except Exception as exc:
                errors.append({"module": name, "error": str(exc)})

        return {
            "source": source,
            "registered": registered,
            "already_existing": already_existing,
            "reactivated": reactivated,
            "updated": updated,
            "ignored": ignored,
            "errors": errors,
            "warnings": warnings,
        }

    except Exception as e:
        db.rollback()

        raise HTTPException(status_code=500, detail=f"Error registering modules: {e}")


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


# ============================================================================
# RUTAS DINÁMICAS PARA MÓDULOS (deben estar al FINAL para evitar conflictos)
# ============================================================================


@router.get("/{module_id}", response_model=ModuloOutSchema)
def get_module(module_id: str, db: Session = Depends(get_db)):
    try:
        module_uuid = uuid.UUID(module_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid module ID format")

    module = db.query(Module).filter_by(id=module_uuid).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return ModuloOutSchema.model_validate(_module_to_response(module))


@router.put("/{module_id}", response_model=ModuloOutSchema)
def update_module(
    module_id: str, module_in: mod_schemas.ModuloCreate, db: Session = Depends(get_db)
):
    try:
        module_uuid = uuid.UUID(module_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid module ID format")

    module = db.query(Module).filter_by(id=module_uuid).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    _update_existing_module(module, module_in.model_dump(), sync_active=True)

    db.add(module)
    db.commit()
    db.refresh(module)

    return ModuloOutSchema.model_validate(_module_to_response(module))


@router.delete("/{module_id}")
def delete_module(
    module_id: str,
    force: bool = Query(False, description="If true, unassigns from tenants before deleting"),
    db: Session = Depends(get_db),
):
    try:
        module_uuid = uuid.UUID(module_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid module ID format")

    module = db.query(Module).filter_by(id=module_uuid).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Si el módulo está asignado a uno o más tenants, bloquear o forzar desasignación
    assignments = (
        db.query(CompanyModule.id).filter(CompanyModule.module_id == module_uuid).limit(1).all()
    )
    if assignments and not force:
        raise HTTPException(
            status_code=409,
            detail="Module is assigned to one or more tenants; unassign before deleting",
        )
    if assignments and force:
        db.query(CompanyModule).filter(CompanyModule.module_id == module_uuid).delete(
            synchronize_session=False
        )

    db.delete(module)
    db.commit()

    return {"ok": True}


@router.post("/{module_id}/activate", response_model=ModuloOutSchema)
def activate_module(module_id: str, db: Session = Depends(get_db)):
    try:
        module_uuid = uuid.UUID(module_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid module ID format")

    module = db.query(Module).filter_by(id=module_uuid).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    module.active = True  # type: ignore[assignment]
    db.add(module)
    db.commit()
    db.refresh(module)

    return ModuloOutSchema.model_validate(_module_to_response(module))


@router.post("/{module_id}/deactivate", response_model=ModuloOutSchema)
def deactivate_module(module_id: str, db: Session = Depends(get_db)):
    try:
        module_uuid = uuid.UUID(module_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid module ID format")

    module = db.query(Module).filter_by(id=module_uuid).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    module.active = False  # type: ignore[assignment]
    db.add(module)
    db.commit()
    db.refresh(module)

    return ModuloOutSchema.model_validate(_module_to_response(module))
