"""
Schemas Pydantic para Recetas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# INGREDIENTES DE RECETA
# ============================================================================


class RecipeIngredientBase(BaseModel):
    # Rechazar campos extra en payload de ingredientes
    model_config = ConfigDict(extra="forbid")
    product_id: UUID
    qty: float = Field(..., gt=0, description="Ingredient quantity")
    unit: str = Field(..., min_length=1, max_length=10)

    # Purchase info
    purchase_packaging: str = Field(..., description="e.g. 'Bag 110 lbs'")
    qty_per_package: float = Field(..., gt=0, description="Quantity per package")
    package_unit: str = Field(..., min_length=1, max_length=10)
    package_cost: float = Field(..., ge=0, description="Package cost")

    notes: str | None = None
    line_order: int = Field(default=0, ge=0)

    @field_validator("unit", "package_unit")
    @classmethod
    def validate_unit(cls, v):
        valid_units = [
            "kg",
            "g",
            "lb",
            "oz",
            "ton",
            "mg",  # Peso
            "L",
            "ml",
            "gal",
            "qt",
            "pt",
            "cup",
            "fl_oz",
            "tbsp",
            "tsp",  # Volumen
            "uds",
            "unidades",
            "pcs",  # Conteo
        ]
        if v.lower() not in [u.lower() for u in valid_units]:
            raise ValueError(f"Unidad no válida: {v}. Usar: {', '.join(valid_units)}")
        return v


class RecipeIngredientCreate(RecipeIngredientBase):
    pass


class RecipeIngredientUpdate(BaseModel):
    # Rechazar campos extra también en updates parciales
    model_config = ConfigDict(extra="forbid")
    product_id: UUID | None = None
    qty: float | None = Field(None, gt=0)
    unit: str | None = None
    purchase_packaging: str | None = None
    qty_per_package: float | None = Field(None, gt=0)
    package_unit: str | None = None
    package_cost: float | None = Field(None, ge=0)
    notes: str | None = None
    line_order: int | None = Field(None, ge=0)


class RecipeIngredientResponse(RecipeIngredientBase):
    id: UUID
    recipe_id: UUID
    ingredient_cost: float | None = 0
    created_at: datetime

    # Info del producto (join)
    product_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# RECETAS
# ============================================================================


class RecipeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    product_id: UUID
    yield_qty: int = Field(..., gt=0, description="Units produced")
    prep_time_minutes: int | None = Field(None, ge=0, description="Minutes")
    instructions: str | None = None
    is_active: bool = True


class RecipeCreate(RecipeBase):
    # Rechazar campos extra en la receta al crear
    model_config = ConfigDict(extra="forbid")
    ingredients: list[RecipeIngredientCreate] = Field(
        default_factory=list, description="Ingredients list (optional on create)"
    )

    @field_validator("ingredients")
    @classmethod
    def validate_ingredients(cls, v):
        if len(v) == 0:
            # Permitir crear receta sin ingredientes inicialmente
            return v

        # Validar que no haya duplicados de productos
        product_ids = [ing.product_id for ing in v]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("No puede haber ingredientes duplicados en la receta")

        return v


class RecipeUpdate(BaseModel):
    # Rechazar campos extra en updates de receta
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, min_length=1, max_length=200)
    product_id: UUID | None = None
    yield_qty: int | None = Field(None, gt=0)
    prep_time_minutes: int | None = Field(None, ge=0)
    instructions: str | None = None
    is_active: bool | None = None
    ingredients: list[RecipeIngredientCreate] | None = None


class RecipeResponse(RecipeBase):
    id: UUID
    tenant_id: UUID
    total_cost: float
    unit_cost: float | None = None
    created_at: datetime
    updated_at: datetime

    # Info del producto (join)
    product_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RecipeDetailResponse(RecipeResponse):
    """Receta con ingredientes incluidos"""

    ingredients: list[RecipeIngredientResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CÁLCULOS Y ANÁLISIS
# ============================================================================


class RecipeCostBreakdownResponse(BaseModel):
    recipe_id: str
    name: str
    yield_qty: int
    total_cost: float
    unit_cost: float
    ingredients_count: int
    breakdown: list[dict]


class ProductionCalculationRequest(BaseModel):
    qty_to_produce: int = Field(..., gt=0, description="Cantidad a producir")
    workers: int | None = Field(1, gt=0, description="Número de trabajadores")


class ProductionCalculationResponse(BaseModel):
    recipe: dict
    qty_to_produce: int
    batches_required: float
    ingredients: list[dict]
    total_production_cost: float
    unit_cost: float

    # Opcional: tiempo estimado
    estimated_time: dict | None = None


class PurchaseOrderRequest(BaseModel):
    qty_to_produce: int = Field(..., gt=0)
    supplier_id: UUID | None = None


class PurchaseOrderResponse(BaseModel):
    recipe_id: str
    recipe_name: str
    qty_to_produce: int
    supplier_id: str | None
    estimated_total: float
    lines: list[dict]
    metadata: dict


class RecipeProfitabilityRequest(BaseModel):
    selling_price: float = Field(..., gt=0, description="Precio de venta")
    indirect_costs_pct: float = Field(
        0.30, ge=0, le=1, description="% costos indirectos (0.30 = 30%)"
    )


class RecipeProfitabilityResponse(BaseModel):
    recipe_id: str
    name: str
    direct_cost: float
    indirect_cost: float
    total_cost: float
    selling_price: float
    profit: float
    margin_percentage: float
    breakeven_units: int


class RecipeComparisonResponse(BaseModel):
    recipes: list[dict]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "recipes": [
                    {
                        "recipe_id": "uuid",
                        "nombre": "Pan Integral",
                        "costo_por_unidad": 0.25,
                        "rendimiento": 100,
                        "ingredientes_count": 8,
                    }
                ]
            }
        }
    )


# ============================================================================
# FILTROS Y PAGINACIÓN
# ============================================================================


class RecipeFilters(BaseModel):
    active: bool | None = None
    product_id: UUID | None = None
    name_contains: str | None = None
    min_cost: float | None = None
    max_cost: float | None = None

    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)
    order_by: str = Field(
        "name", pattern="^(name|unit_cost|yield_qty|created_at)$"
    )
    order_dir: str = Field("asc", pattern="^(asc|desc)$")
