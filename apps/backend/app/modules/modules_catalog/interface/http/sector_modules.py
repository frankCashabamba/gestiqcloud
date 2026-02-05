"""
Endpoint para obtener módulos filtrados por sector
FASE: Multi-sector module availability control
No hardcodeos - todo configurable dinámicamente desde modules_catalog.py
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.settings.application.modules_catalog import get_available_modules

# ============================================================================
# Response Models
# ============================================================================


class ModuleInfo(BaseModel):
    """Información de un módulo"""

    id: str
    name: str
    icon: str
    category: str
    description: str
    required: bool
    default_enabled: bool
    dependencies: list[str]
    countries: list[str]
    sectors: list[str] | None = (
        None  # None = available for all, [] = none, ["retail", ...] = specific
    )


class GetModulesResponse(BaseModel):
    """Respuesta con módulos disponibles para el sector"""

    sector: str | None
    modules: list[ModuleInfo]
    total: int


# ============================================================================
# Router
# ============================================================================

router = APIRouter(
    prefix="/modules",
    tags=["Modulos"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


@router.get("/sector", response_model=GetModulesResponse)
def get_sector_modules(
    request: Request,
    db: Session = Depends(get_db),
    sector: str | None = None,
    country: str | None = None,
):
    """
    Obtiene módulos disponibles para un sector específico.

    Query parameters:
    - sector: Código del sector (ej: 'retail', 'bakery', 'workshop')
    - country: Código ISO del país (ej: 'ES', 'EC')

    Sin parámetros, devuelve todos los módulos disponibles.
    """
    try:
        # Obtener módulos filtrados dinámicamente
        modules = get_available_modules(country=country, sector=sector)

        # Mapear a response model
        module_list = [ModuleInfo(**m) for m in modules]

        return GetModulesResponse(
            sector=sector,
            modules=module_list,
            total=len(module_list),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving modules: {str(e)}",
        )
