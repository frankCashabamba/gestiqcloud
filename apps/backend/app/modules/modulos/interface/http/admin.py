from __future__ import annotations

from fastapi import APIRouter, Depends
from apps.backend.app.shared.utils import ping_ok
import json
from sqlalchemy.orm import Session

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.config.settings import settings
from app.modules.modulos.application.use_cases import ListarModulosAdmin
from app.modules.modulos.infrastructure.repositories import SqlModuloRepo
from app.modules.modulos.interface.http.schemas import ModuloOutSchema
from app.modules import crud as mod_crud, schemas as mod_schemas, services as mod_services
from app.models.empresa.empresa import Empresa
from app.models.core.modulo import EmpresaModulo, Modulo
from fastapi import HTTPException
import os
from pathlib import Path


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
        candidates.extend([
            repo_root / "apps" / "tenant" / "src" / "modules",
            repo_root / "apps" / "src" / "modules",
        ])

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
        "importador": None,
        "importador_excel": None,
    }
    cat_map: dict[str, str | None] = {
        "ventas": "operaciones",
        "compras": "operaciones",
        "facturacion": "operaciones",
        "inventario": "operaciones",
        "rrhh": "operaciones",
        "importador": "herramientas",
        "importador_excel": "herramientas",
    }
    return icon_map.get(s), cat_map.get(s)

def _guess_defaults(slug: str) -> tuple[str, str | None]:
    """Infer icon and category from common slug names when no manifest is present."""
    s = slug.lower()
    icon_map = {
        "ventas": "🧾",
        "compras": "🧾",
        "facturacion": "🧾",
        "inventario": "📦",
        "contabilidad": "📒",
        "finanzas": "💳",
        "proveedores": "🏷️",
        "clientes": "👥",
        "rrhh": "👤",
        "importador": "⬆️",
        "settings": "⚙️",
    }
    cat_map = {
        "ventas": "operaciones",
        "compras": "operaciones",
        "facturacion": "operaciones",
        "inventario": "operaciones",
        "contabilidad": "finanzas",
        "finanzas": "finanzas",
        "proveedores": "maestros",
        "clientes": "maestros",
        "rrhh": "operaciones",
        "importador": "herramientas",
        "settings": "configuracion",
    }
    return icon_map.get(s, "📦"), cat_map.get(s)


@router.get("/ping")
def ping_admin_modulos():
    return ping_ok()


@router.post("/empresa/{empresa_id}/usuarios/{usuario_id}", response_model=mod_schemas.ModuloAsignadoOut)
def asignar_modulo_a_usuario(
    empresa_id: int,
    usuario_id: int,
    modulo_in: mod_schemas.ModuloAsignadoCreate,
    db: Session = Depends(get_db),
):
    return mod_services.asignar_modulo_a_usuario_si_empresa_lo_tiene(
        db, empresa_id, usuario_id, modulo_in.modulo_id
    )


@router.get("/empresa/{empresa_id}/usuarios/{usuario_id}", response_model=list[mod_schemas.ModuloAsignadoOut])
def listar_modulos_de_usuario(
    empresa_id: int,
    usuario_id: int,
    db: Session = Depends(get_db),
):
    return mod_crud.obtener_modulos_de_usuario(db, empresa_id, usuario_id)


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
def registrar_modulos(db: Session = Depends(get_db)):
    modules_dir = _resolve_modules_dir()
    if not modules_dir:
        raise HTTPException(status_code=500, detail="FRONTEND_MODULES_PATH no está configurado en el backend")
    if not os.path.isdir(modules_dir):
        raise HTTPException(status_code=500, detail=f"FRONTEND_MODULES_PATH no existe o no es un directorio: {modules_dir}")
    try:
        carpetas = [
            nombre for nombre in os.listdir(modules_dir)
            if os.path.isdir(os.path.join(modules_dir, nombre))
        ]
        registrados: list[str] = []
        ya_existentes: list[str] = []
        ignorados: list[str] = []
        errores: list[dict] = []
        for carpeta in carpetas:
            # ignorar carpetas especiales
            if carpeta.startswith('.') or carpeta.startswith('_'):
                ignorados.append(carpeta)
                continue
            # Aceptar módulos con Panel.tsx o Routes.tsx para el loader dinámico
            panel_path = os.path.join(modules_dir, carpeta, "Panel.tsx")
            routes_path = os.path.join(modules_dir, carpeta, "Routes.tsx")
            # Aceptar si existe cualquier archivo .tsx en la carpeta (además de Panel/Routes)
            if not (os.path.exists(panel_path) or os.path.exists(routes_path) or any(fn.lower().endswith('.tsx') for fn in os.listdir(os.path.join(modules_dir, carpeta)))):
                ignorados.append(carpeta)
                continue
            nombre = carpeta.lower()
            existente = db.query(Modulo).filter_by(nombre=nombre).first()
            if existente:
                ya_existentes.append(nombre)
                continue
            # Intentar leer manifest opcional (module.json)
            manifest_path = os.path.join(modules_dir, carpeta, "module.json")
            manifest: dict | None = None
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as fh:
                        manifest = json.load(fh)
                except Exception as me:
                    errores.append({"modulo": nombre, "error": f"manifest invalido: {me}"})
            # Construir payload combinando defaults + manifest
            # Use v2 defaults (emoji + categories) when no manifest is present
            default_icon, default_cat = _guess_defaults_v2(nombre)
            # Si no hay manifest, intente usar como plantilla el primer .tsx encontrado
            plantilla_detectada = None
            try:
                for _fn in os.listdir(os.path.join(modules_dir, carpeta)):
                    if _fn.lower().endswith('.tsx'):
                        plantilla_detectada = _fn.rsplit('.', 1)[0]
                        break
            except Exception:
                pass
            payload = {
                "nombre": nombre,
                "url": (manifest.get("url") if manifest else nombre) or nombre,
                "icono": (manifest.get("icono") if manifest else default_icon) or default_icon,
                "activo": manifest.get("activo", True) if manifest else True,
                "plantilla_inicial": (manifest.get("plantilla_inicial", plantilla_detectada or nombre) if manifest else (plantilla_detectada or nombre)),
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
                registrados.append(nombre)
            except Exception as ce:
                errores.append({"modulo": nombre, "error": str(ce)})
        return {"registrados": registrados, "ya_existentes": ya_existentes, "ignorados": ignorados, "errores": errores}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar módulos: {e}")


@router.post("/empresa/{empresa_id}", response_model=mod_schemas.EmpresaModuloOut)
def asignar_modulo_a_empresa(empresa_id: int, modulo_in: mod_schemas.EmpresaModuloCreate, db: Session = Depends(get_db)):
    return mod_services.asignar_modulo_a_empresa_si_no_existe(db, empresa_id, modulo_in)


@router.get("/empresa/{empresa_id}", response_model=list[mod_schemas.EmpresaModuloOut])
def listar_modulos_de_empresa(empresa_id: int, db: Session = Depends(get_db)):
    registros = mod_crud.obtener_modulos_de_empresa(db, empresa_id)
    resultado = []
    for r in registros:
        resultado.append({
            "id": r.id,
            "empresa_id": r.empresa_id,
            "empresa_slug": r.empresa.slug,
            "activo": r.activo,
            "fecha_activacion": r.fecha_activacion,
            "modulo_id": r.modulo_id,
            "modulo": r.modulo,
            "fecha_expiracion": r.fecha_expiracion,
        })
    return resultado


@router.post("/empresa/{empresa_id}/upsert", response_model=mod_schemas.EmpresaModuloOutAdmin)
def upsert_modulo_empresa(empresa_id: int, modulo_in: mod_schemas.EmpresaModuloCreate, db: Session = Depends(get_db)):
    return mod_services.upsert_modulo_a_empresa(db, empresa_id, modulo_in)


@router.delete("/empresa/{empresa_id}/modulo/{modulo_id}")
def eliminar_modulo_de_empresa(empresa_id: int, modulo_id: int, db: Session = Depends(get_db)):
    empresa_modulo = db.query(EmpresaModulo).filter_by(empresa_id=empresa_id, modulo_id=modulo_id).first()
    if not empresa_modulo:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
    db.delete(empresa_modulo)
    db.commit()
    return {"ok": True}

