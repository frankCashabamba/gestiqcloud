"""
Service layer para operaciones de Sector Templates.

Centraliza lógica común para evitar duplicación de código en routers.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.company.company import SectorTemplate


def get_sector_or_404(code: str, db: Session) -> SectorTemplate:
    """
    Obtiene un sector por código o lanza HTTPException 404.

    ✅ Centraliza la lógica de búsqueda
    ✅ Filtra por is_active == True
    ✅ Evita duplicación en routers
    ✅ Busca por código primero, luego por nombre (case-insensitive)

    Args:
        code: Código del sector (se convierte a lowercase)
        db: Session de SQLAlchemy

    Raises:
        HTTPException: 404 si no se encuentra

    Returns:
        SectorTemplate activo

    Ejemplo:
        sector = get_sector_or_404('panaderia', db)
    """
    code_lower = code.lower()
    
    # Intenta primero por código exacto
    sector = (
        db.query(SectorTemplate)
        .filter(
            SectorTemplate.code == code_lower,
            SectorTemplate.is_active == True,  # noqa: E712
        )
        .first()
    )

    # Si no encontrado por código, intenta por nombre (case-insensitive)
    if not sector:
        from sqlalchemy import func
        sector = (
            db.query(SectorTemplate)
            .filter(
                func.lower(SectorTemplate.name) == code_lower,
                SectorTemplate.is_active == True,  # noqa: E712
            )
            .first()
        )

    if not sector:
        raise HTTPException(status_code=404, detail=f"Sector '{code}' no encontrado")

    return sector
