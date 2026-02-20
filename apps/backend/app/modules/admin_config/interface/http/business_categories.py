"""
Router for Business Categories (Business Types)

Endpoint: /api/v1/business-categories
Returns business categories available from DB
Replaces previous hardcoding
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.company.company import BusinessCategory

router = APIRouter(prefix="/api/v1/business-categories", tags=["Business Categories"])


@router.get("/", summary="List business categories")
async def list_business_categories(db: Session = Depends(get_db)):
    """
    Get all active business categories from DB.

    Replaces previous hardcoding that was in frontend.

    Returns:
        {
            "ok": true,
            "count": 4,
            "categories": [
                {
                    "id": "uuid...",
                    "code": "retail",
                    "name": "Retail / Store",
                    "description": "Retail commerce"
                },
                ...
            ]
        }
    """
    try:
        categories = (
            db.query(BusinessCategory)
            .filter(BusinessCategory.is_active == True)  # noqa: E712
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
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")


@router.get("/{code}", summary="Get category by code")
async def get_business_category_by_code(code: str, db: Session = Depends(get_db)):
    """
    Get a specific category by its code.

    Args:
        code: Category code (e.g., 'retail')

    Returns:
        {
            "ok": true,
            "category": {
                "id": "uuid...",
                "code": "retail",
                "name": "Retail / Store",
                "description": "Retail commerce",
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
            raise HTTPException(status_code=404, detail=f"Category '{code}' not found")

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
        raise HTTPException(status_code=500, detail=f"Error fetching category: {str(e)}")
