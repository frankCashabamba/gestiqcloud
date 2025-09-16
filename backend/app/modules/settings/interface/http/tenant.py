from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from ...infrastructure.repositories import SettingsRepo
from app.models.empresa.empresa import Empresa
from app.models.empresa.settings import ConfiguracionEmpresa

router = APIRouter()


@router.get("/general")
def get_general(db: Session = Depends(get_db)):
    return SettingsRepo(db).get("general")


@router.put("/general")
def put_general(payload: dict, db: Session = Depends(get_db)):
    SettingsRepo(db).put("general", payload)
    return {"ok": True}


@router.get("/branding")
def get_branding(db: Session = Depends(get_db)):
    return SettingsRepo(db).get("branding")


@router.put("/branding")
def put_branding(payload: dict, db: Session = Depends(get_db)):
    SettingsRepo(db).put("branding", payload)
    return {"ok": True}


@router.get("/fiscal")
def get_fiscal(db: Session = Depends(get_db)):
    return SettingsRepo(db).get("fiscal")


@router.put("/fiscal")
def put_fiscal(payload: dict, db: Session = Depends(get_db)):
    SettingsRepo(db).put("fiscal", payload)
    return {"ok": True}


@router.get("/horarios")
def get_horarios(db: Session = Depends(get_db)):
    return SettingsRepo(db).get("horarios")


@router.put("/horarios")
def put_horarios(payload: dict, db: Session = Depends(get_db)):
    SettingsRepo(db).put("horarios", payload)
    return {"ok": True}


@router.get("/limites")
def get_limites(db: Session = Depends(get_db)):
    return SettingsRepo(db).get("limites")


@router.put("/limites")
def put_limites(payload: dict, db: Session = Depends(get_db)):
    SettingsRepo(db).put("limites", payload)
    return {"ok": True}


@router.get("/theme")
def get_theme_tokens(db: Session = Depends(get_db), empresa: str | None = Query(default=None)):
    """Return design tokens for theming the tenant UI.

    Combines stored sections (branding/general) into a normalized token shape
    consumible por el frontend.
    """
    # If empresa is provided (vanity URL flow), derive theme from core_configuracionempresa
    if empresa:
        emp = (
            db.query(Empresa)
            .filter((Empresa.slug == empresa) | (Empresa.nombre == empresa))
            .first()
        )
        cfg = None
        if emp:
            cfg = db.query(ConfiguracionEmpresa).filter(ConfiguracionEmpresa.empresa_id == emp.id).first()

        brand_name = emp.nombre if emp else ""
        logo_url = (getattr(cfg, "logo_empresa", None) or getattr(emp, "logo", None)) if (cfg or emp) else None
        color_primary = getattr(cfg, "color_primario", None) or getattr(emp, "color_primario", None) or "#0ea5e9"
        sector = getattr(emp, "plantilla_inicio", None) or "default"

        return {
            "brand": { "name": brand_name, "logoUrl": logo_url, "faviconUrl": None },
            "colors": {
                "primary": color_primary,
                "onPrimary": "#ffffff",
                "bg": "#ffffff",
                "fg": "#0f172a",
                "muted": "#64748b",
                "success": "#10b981",
                "warning": "#f59e0b",
                "danger": "#ef4444",
            },
            "typography": { "fontFamily": "Inter, system-ui, sans-serif", "fontSizeBase": "16px" },
            "radius": { "sm": "4px", "md": "8px", "lg": "12px" },
            "shadows": { "sm": "0 1px 2px rgba(0,0,0,.08)", "md": "0 4px 12px rgba(0,0,0,.12)" },
            "mode": "light",
            "components": {},
            "sector": sector,
        }

    # Default behavior: return safe defaults without hitting tenant_settings
    return {
        "brand": { "name": "", "logoUrl": None, "faviconUrl": None },
        "colors": {
            "primary": "#0ea5e9",
            "onPrimary": "#ffffff",
            "bg": "#ffffff",
            "fg": "#0f172a",
            "muted": "#64748b",
            "success": "#10b981",
            "warning": "#f59e0b",
            "danger": "#ef4444",
        },
        "typography": { "fontFamily": "Inter, system-ui, sans-serif", "fontSizeBase": "16px" },
        "radius": { "sm": "4px", "md": "8px", "lg": "12px" },
        "shadows": { "sm": "0 1px 2px rgba(0,0,0,.08)", "md": "0 4px 12px rgba(0,0,0,.12)" },
        "mode": "light",
        "components": {},
    }
