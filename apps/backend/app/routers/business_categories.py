"""
Router para Business Categories (Tipos de Negocio)

Endpoint: /api/v1/business-categories
Retorna las categorías de negocio disponibles desde BD
Reemplaza hardcoding anterior
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.company.company import BusinessCategory

router = APIRouter(prefix="/api/v1/business-categories", tags=["Business Categories"])


@router.get("/", summary="Listar categorías de negocio")
async def list_business_categories(db: Session = Depends(get_db)):
    """
    Obtiene todas las categorías de negocio activas desde BD.

    Reemplaza hardcoding anterior que estaba en frontend.

    Returns:
        {
            "ok": true,
            "count": 4,
            "categories": [
                {
                    "id": "uuid...",
                    "code": "retail",
                    "name": "Retail / Tienda",
                    "description": "Comercio minorista"
                },
                ...
            ]
        }
    """
    try:
        categories = (
            db.query(BusinessCategory)
            .filter(
                BusinessCategory.is_active == True  # noqa: E712
            )
            .all()
        )

        return {
            "ok": True,
            "count": len(categories),
            "categories": [
                {"id": str(c.id), "code": c.code, "name": c.name, "description": c.description}
                for c in categories
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener categorías: {str(e)}")


@router.get("/{code}", summary="Obtener categoría por código")
async def get_business_category_by_code(code: str, db: Session = Depends(get_db)):
    """
    Obtiene una categoría específica por su código.

    Args:
        code: Código de la categoría (ej: 'retail')

    Returns:
        {
            "ok": true,
            "category": {
                "id": "uuid...",
                "code": "retail",
                "name": "Retail / Tienda",
                "description": "Comercio minorista",
                "is_active": true
            }
        }
    """
    try:
        category = (
            db.query(BusinessCategory)
            .filter(
                BusinessCategory.code == code.lower(),
                BusinessCategory.is_active == True,  # noqa: E712
            )
            .first()
        )

        if not category:
            raise HTTPException(status_code=404, detail=f"Categoría '{code}' no encontrada")

        return {
            "ok": True,
            "category": {
                "id": str(category.id),
                "code": category.code,
                "name": category.name,
                "description": category.description,
                "is_active": category.is_active,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener categoría: {str(e)}")
