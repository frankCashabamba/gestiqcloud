"""
Router para Cost Periods (costeo mensual).

Endpoints:
- GET /cost-periods (lista períodos)
- POST /cost-periods (crear período)
- GET /cost-periods/{period_id} (detalle)
- PUT /cost-periods/{period_id} (actualizar)
- DELETE /cost-periods/{period_id} (eliminar/desactivar)
- POST /cost-periods/{period_id}/close (cierre formal)
- GET /cost-periods/{period_id}/validate (validar período)
- GET /cost-periods/{period_id}/impact (impacto en recetas)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.production._cost_periods import CostPeriod
from app.schemas.cost_periods import (
    CostPeriodCreate,
    CostPeriodDetailResponse,
    CostPeriodResponse,
    CostPeriodSummary,
    CostPeriodUpdate,
    CostPeriodValidationResult,
)
from app.services.cost_periods_service import CostPeriodsService

router = APIRouter(prefix="/cost-periods", tags=["Cost Periods"])


@router.get("", response_model=list[CostPeriodSummary])
def list_cost_periods(
    db: Session = Depends(get_db),
    tenant_id: str = Query(..., description="Tenant ID"),
    active_only: bool = Query(True),
):
    """
    Lista períodos de costeo del tenant.
    """
    query = db.query(CostPeriod).filter(CostPeriod.tenant_id == UUID(tenant_id))
    if active_only:
        query = query.filter(CostPeriod.is_active == True)
    return query.order_by(CostPeriod.month.desc()).all()


@router.post("", response_model=CostPeriodResponse)
def create_cost_period(
    period_data: CostPeriodCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Query(...),
):
    """
    Crea un nuevo período de costeo.
    
    Los campos computed (labor_burden_factor, diesel_per_oven_hour, electricity_per_hour)
    se calculan automáticamente en la base de datos.
    
    Ejemplo:
    ```
    {
        "month": "2025-02",
        "labor_hour_rate": 4.00,
        "labor_paid_hours": 160,
        "touch_hours_total": 150,
        "electricity_cost": 100,
        "diesel_cost_month": 64,
        "oven_hours_total": 160
    }
    ```
    """
    service = CostPeriodsService(db, UUID(tenant_id))

    # Validar que no exista período para ese mes
    existing = service.get_period(period_data.month)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Period {period_data.month} already exists"
        )

    period = service.create_period(
        month=period_data.month,
        labor_hour_rate=period_data.labor_hour_rate,
        labor_paid_hours=period_data.labor_paid_hours,
        touch_hours_total=period_data.touch_hours_total,
        electricity_cost=period_data.electricity_cost,
        diesel_cost_month=period_data.diesel_cost_month,
        oven_hours_total=period_data.oven_hours_total,
        production_share_pct=period_data.production_share_pct,
        notes=period_data.notes,
    )
    return period


@router.get("/{period_id}", response_model=CostPeriodDetailResponse)
def get_cost_period(period_id: UUID, db: Session = Depends(get_db)):
    """Obtiene detalle de un período."""
    period = db.query(CostPeriod).filter(CostPeriod.id == period_id).first()
    if not period:
        raise HTTPException(status_code=404, detail="Period not found")

    # Calcular totales
    labor_cost = float(period.labor_hour_rate) * float(period.labor_paid_hours)
    indirect_cost = float(period.electricity_cost) + float(period.diesel_cost_month)
    total_cost = labor_cost + indirect_cost

    response = CostPeriodDetailResponse.model_validate(period)
    response.total_labor_cost = labor_cost
    response.total_indirect_cost = indirect_cost
    response.total_cost = total_cost

    return response


@router.put("/{period_id}", response_model=CostPeriodResponse)
def update_cost_period(
    period_id: UUID,
    period_data: CostPeriodUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Query(...),
):
    """Actualiza un período."""
    service = CostPeriodsService(db, UUID(tenant_id))

    try:
        period = service.update_period(
            period_id,
            **period_data.model_dump(exclude_unset=True)
        )
        return period
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{period_id}")
def delete_cost_period(
    period_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Query(...),
):
    """Desactiva un período (soft delete)."""
    service = CostPeriodsService(db, UUID(tenant_id))

    try:
        service.update_period(period_id, is_active=False)
        return {"detail": "Period deactivated"}
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# VALIDACIÓN Y ANÁLISIS
# ============================================================================


@router.get("/{period_id}/validate", response_model=CostPeriodValidationResult)
def validate_cost_period(
    period_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Query(...),
):
    """
    Valida un período y retorna warnings/errors.
    
    Checks realizados:
    - labor_burden_factor entre 0.8 y 1.6 (eficiencia)
    - oven_hours_total > 10 (no subutilizado)
    - touch_hours_total ≈ labor_paid_hours (no mucho tiempo muerto)
    """
    service = CostPeriodsService(db, UUID(tenant_id))

    try:
        result = service.validate_period(period_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{period_id}/impact")
def get_period_impact(
    period_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Query(...),
):
    """
    Calcula el impacto de aplicar este período a todas las recetas del tenant.
    
    Retorna:
    - Recetas afectadas y cambios de costo
    - Estadísticas agregadas
    - Impacto porcentual promedio
    """
    service = CostPeriodsService(db, UUID(tenant_id))

    try:
        impact = service.get_period_impact_on_recipes(period_id)
        return impact
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{period_id}/close")
def close_cost_period(
    period_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Query(...),
):
    """
    Cierra formalmente un período.
    
    Esto marca el período como finalizado y permite hacer recálculos históricos
    si es necesario.
    """
    service = CostPeriodsService(db, UUID(tenant_id))

    try:
        period = service.close_period(period_id)
        return {
            "detail": f"Period {period.month} closed",
            "closed_at": period.closed_at,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# DATOS ESPECIALES
# ============================================================================


@router.get("/current")
def get_current_cost_period(
    db: Session = Depends(get_db),
    tenant_id: str = Query(...),
):
    """
    Obtiene el período de costeo actual (más reciente activo).
    """
    service = CostPeriodsService(db, UUID(tenant_id))
    period = service.get_current_period()

    if not period:
        raise HTTPException(status_code=404, detail="No active cost period found")

    return period


@router.get("/by-month/{month}")
def get_cost_period_by_month(
    month: str,
    db: Session = Depends(get_db),
    tenant_id: str = Query(...),
):
    """
    Obtiene un período específico por mes (YYYY-MM).
    """
    service = CostPeriodsService(db, UUID(tenant_id))
    period = service.get_period(month)

    if not period:
        raise HTTPException(status_code=404, detail=f"Period {month} not found")

    return period
