"""
Schemas Pydantic para Recetas
"""

from pydantic import BaseModel, Field, validator, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime


# ============================================================================
# INGREDIENTES DE RECETA
# ============================================================================


class RecipeIngredientBase(BaseModel):
    # Rechazar campos extra en payload de ingredientes
    model_config = ConfigDict(extra='forbid')
    producto_id: UUID
    qty: float = Field(..., gt=0, description="Cantidad del ingrediente")
    unidad_medida: str = Field(..., min_length=1, max_length=10)

    # Info de compra
    presentacion_compra: str = Field(..., description="Ej: 'Saco 110 lbs'")
    qty_presentacion: float = Field(..., gt=0, description="Cantidad en presentación")
    unidad_presentacion: str = Field(..., min_length=1, max_length=10)
    costo_presentacion: float = Field(..., ge=0, description="Costo de la presentación")

    notas: Optional[str] = None
    orden: int = Field(default=0, ge=0)

    @validator("unidad_medida", "unidad_presentacion")
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
    model_config = ConfigDict(extra='forbid')
    producto_id: Optional[UUID] = None
    qty: Optional[float] = Field(None, gt=0)
    unidad_medida: Optional[str] = None
    presentacion_compra: Optional[str] = None
    qty_presentacion: Optional[float] = Field(None, gt=0)
    unidad_presentacion: Optional[str] = None
    costo_presentacion: Optional[float] = Field(None, ge=0)
    notas: Optional[str] = None
    orden: Optional[int] = Field(None, ge=0)


class RecipeIngredientResponse(RecipeIngredientBase):
    id: UUID
    recipe_id: UUID
    costo_ingrediente: Optional[float] = 0
    created_at: datetime

    # Info del producto (join)
    producto_nombre: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# RECETAS
# ============================================================================


class RecipeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    product_id: UUID
    rendimiento: int = Field(..., gt=0, description="Unidades producidas")
    tiempo_preparacion: Optional[int] = Field(None, ge=0, description="Minutos")
    instrucciones: Optional[str] = None
    active: bool = True


class RecipeCreate(RecipeBase):
    # Rechazar campos extra en la receta al crear
    model_config = ConfigDict(extra='forbid')
    ingredientes: List[RecipeIngredientCreate] = Field(
        default_factory=list, description="Lista de ingredientes (opcional en creación)"
    )

    @validator("ingredientes")
    def validate_ingredients(cls, v):
        if len(v) == 0:
            # Permitir crear receta sin ingredientes inicialmente
            return v

        # Validar que no haya duplicados de productos
        producto_ids = [ing.producto_id for ing in v]
        if len(producto_ids) != len(set(producto_ids)):
            raise ValueError("No puede haber ingredientes duplicados en la receta")

        return v


class RecipeUpdate(BaseModel):
    # Rechazar campos extra en updates de receta
    model_config = ConfigDict(extra='forbid')
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    product_id: Optional[UUID] = None
    rendimiento: Optional[int] = Field(None, gt=0)
    tiempo_preparacion: Optional[int] = Field(None, ge=0)
    instrucciones: Optional[str] = None
    active: Optional[bool] = None
    ingredientes: Optional[List[RecipeIngredientCreate]] = None


class RecipeResponse(RecipeBase):
    id: UUID
    tenant_id: UUID
    costo_total: float
    costo_por_unidad: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    # Info del producto (join)
    producto_nombre: Optional[str] = None

    class Config:
        from_attributes = True


class RecipeDetailResponse(RecipeResponse):
    """Receta con ingredientes incluidos"""

    ingredientes: List[RecipeIngredientResponse] = []

    class Config:
        from_attributes = True


# ============================================================================
# CÁLCULOS Y ANÁLISIS
# ============================================================================


class RecipeCostBreakdownResponse(BaseModel):
    recipe_id: str
    name: str
    rendimiento: int
    costo_total: float
    costo_por_unidad: float
    ingredientes_count: int
    desglose: List[dict]


class ProductionCalculationRequest(BaseModel):
    qty_to_produce: int = Field(..., gt=0, description="Cantidad a producir")
    workers: Optional[int] = Field(1, gt=0, description="Número de trabajadores")


class ProductionCalculationResponse(BaseModel):
    recipe: dict
    qty_to_produce: int
    batches_required: float
    ingredientes: List[dict]
    costo_total_produccion: float
    costo_por_unidad: float

    # Opcional: tiempo estimado
    tiempo_estimado: Optional[dict] = None


class PurchaseOrderRequest(BaseModel):
    qty_to_produce: int = Field(..., gt=0)
    supplier_id: Optional[UUID] = None


class PurchaseOrderResponse(BaseModel):
    recipe_id: str
    recipe_nombre: str
    qty_to_produce: int
    supplier_id: Optional[str]
    total_estimado: float
    lineas: List[dict]
    metadata: dict


class RecipeProfitabilityRequest(BaseModel):
    selling_price: float = Field(..., gt=0, description="Precio de venta")
    indirect_costs_pct: float = Field(
        0.30, ge=0, le=1, description="% costos indirectos (0.30 = 30%)"
    )


class RecipeProfitabilityResponse(BaseModel):
    recipe_id: str
    name: str
    costo_directo: float
    costo_indirecto: float
    costo_total: float
    precio_venta: float
    ganancia: float
    margen_porcentaje: float
    punto_equilibrio_unidades: int


class RecipeComparisonResponse(BaseModel):
    recipes: List[dict]

    class Config:
        json_schema_extra = {
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


# ============================================================================
# FILTROS Y PAGINACIÓN
# ============================================================================


class RecipeFilters(BaseModel):
    active: Optional[bool] = None
    product_id: Optional[UUID] = None
    nombre_contains: Optional[str] = None
    costo_min: Optional[float] = None
    costo_max: Optional[float] = None

    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)
    order_by: str = Field(
        "nombre", pattern="^(nombre|costo_por_unidad|rendimiento|created_at)$"
    )
    order_dir: str = Field("asc", pattern="^(asc|desc)$")
