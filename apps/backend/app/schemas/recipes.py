"""
Schemas Pydantic para Recetas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, validator

# ============================================================================
# INGREDIENTES DE RECETA
# ============================================================================


class RecipeIngredientBase(BaseModel):
    # Rechazar campos extra en payload de ingredientes
    model_config = ConfigDict(extra="forbid")
    producto_id: UUID
    qty: float = Field(..., gt=0, description="Cantidad del ingrediente")
    unidad_medida: str = Field(..., min_length=1, max_length=10)

    # Info de compra
    presentacion_compra: str = Field(..., description="Ej: 'Saco 110 lbs'")
    qty_presentacion: float = Field(..., gt=0, description="Cantidad en presentación")
    unidad_presentacion: str = Field(..., min_length=1, max_length=10)
    costo_presentacion: float = Field(..., ge=0, description="Costo de la presentación")

    notas: str | None = None
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
    model_config = ConfigDict(extra="forbid")
    producto_id: UUID | None = None
    qty: float | None = Field(None, gt=0)
    unidad_medida: str | None = None
    presentacion_compra: str | None = None
    qty_presentacion: float | None = Field(None, gt=0)
    unidad_presentacion: str | None = None
    costo_presentacion: float | None = Field(None, ge=0)
    notas: str | None = None
    orden: int | None = Field(None, ge=0)


class RecipeIngredientResponse(RecipeIngredientBase):
    id: UUID
    recipe_id: UUID
    costo_ingrediente: float | None = 0
    created_at: datetime

    # Info del producto (join)
    producto_nombre: str | None = None

    class Config:
        from_attributes = True


# ============================================================================
# RECETAS
# ============================================================================


class RecipeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    product_id: UUID
    rendimiento: int = Field(..., gt=0, description="Unidades producidas")
    tiempo_preparacion: int | None = Field(None, ge=0, description="Minutos")
    instrucciones: str | None = None
    active: bool = True


class RecipeCreate(RecipeBase):
    # Rechazar campos extra en la receta al crear
    model_config = ConfigDict(extra="forbid")
    ingredientes: list[RecipeIngredientCreate] = Field(
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
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, min_length=1, max_length=200)
    product_id: UUID | None = None
    rendimiento: int | None = Field(None, gt=0)
    tiempo_preparacion: int | None = Field(None, ge=0)
    instrucciones: str | None = None
    active: bool | None = None
    ingredientes: list[RecipeIngredientCreate] | None = None


class RecipeResponse(RecipeBase):
    id: UUID
    tenant_id: UUID
    costo_total: float
    costo_por_unidad: float | None = None
    created_at: datetime
    updated_at: datetime

    # Info del producto (join)
    producto_nombre: str | None = None

    class Config:
        from_attributes = True


class RecipeDetailResponse(RecipeResponse):
    """Receta con ingredientes incluidos"""

    ingredientes: list[RecipeIngredientResponse] = []

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
    desglose: list[dict]


class ProductionCalculationRequest(BaseModel):
    qty_to_produce: int = Field(..., gt=0, description="Cantidad a producir")
    workers: int | None = Field(1, gt=0, description="Número de trabajadores")


class ProductionCalculationResponse(BaseModel):
    recipe: dict
    qty_to_produce: int
    batches_required: float
    ingredientes: list[dict]
    costo_total_produccion: float
    costo_por_unidad: float

    # Opcional: tiempo estimado
    tiempo_estimado: dict | None = None


class PurchaseOrderRequest(BaseModel):
    qty_to_produce: int = Field(..., gt=0)
    supplier_id: UUID | None = None


class PurchaseOrderResponse(BaseModel):
    recipe_id: str
    recipe_nombre: str
    qty_to_produce: int
    supplier_id: str | None
    total_estimado: float
    lineas: list[dict]
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
    recipes: list[dict]

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
    active: bool | None = None
    product_id: UUID | None = None
    nombre_contains: str | None = None
    costo_min: float | None = None
    costo_max: float | None = None

    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)
    order_by: str = Field("nombre", pattern="^(nombre|costo_por_unidad|rendimiento|created_at)$")
    order_dir: str = Field("asc", pattern="^(asc|desc)$")
