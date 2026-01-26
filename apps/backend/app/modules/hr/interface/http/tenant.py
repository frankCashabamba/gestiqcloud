"""
RRHH Module - HTTP API Tenant Interface

Funcionalidades completas:
- Gestión de empleados (CRUD completo)
- Gestión de vacaciones (CRUD + aprobación/rechazo)
- Gestión de nóminas (CRUD completo)
- Calculadora de nóminas (devengos, deducciones, impuestos)
- Aprobación y pago de nóminas
- Estadísticas de nóminas por período

Multi-país: España (IRPF, Seg. Social) y Ecuador (IR, IESS)

MIGRADO DE:
- app/routers/hr.py (empleados + vacaciones)
- app/routers/hr_complete.py (nóminas)
"""

from datetime import datetime
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls

# Models
from app.models.hr import Empleado, Vacacion
from app.models.hr.payroll import Payroll as Payroll
from app.models.hr.payroll import PayrollConcept as PayrollConcept
from app.models.tenant import Tenant

# Schemas - Empleados y Vacaciones
from app.schemas.hr import (
    EmpleadoCreate,
    EmpleadoList,
    EmpleadoResponse,
    EmpleadoUpdate,
    VacacionCreate,
    VacacionList,
    VacacionResponse,
)

# Schemas - Payroll
from app.schemas.payroll import (
    PayrollApproveRequest,
    PayrollCalculateRequest,
    PayrollCalculateResponse,
    PayrollConceptCreate,
    PayrollCreate,
    PayrollList,
    PayrollPayRequest,
    PayrollResponse,
    PayrollStats,
    PayrollUpdate,
)

router = APIRouter(
    prefix="/hr",
    tags=["Human Resources"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# HELPERS - Funciones auxiliares de nóminas
# ============================================================================


def _get_tenant_country(db: Session, tenant_id: UUID) -> str:
    """
    Obtiene el país del tenant desde la base de datos.
    
    Retorna el country_code del tenant o "ES" como fallback.
    Los valores válidos son códigos ISO 3166-1 alpha-2 (ES, EC, AR, etc.)
    """
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    tenant = db.execute(stmt).scalar_one_or_none()
    
    if tenant and tenant.country_code:
        return tenant.country_code.upper()
    
    # Fallback a España si no está configurado
    return "ES"


def _generate_numero_nomina(db: Session, tenant_id: UUID, mes: int, ano: int) -> str:
    """Genera número único de nómina: NOM-YYYY-MM-NNNN"""
    prefix = f"NOM-{ano}-{mes:02d}-"

    stmt = (
        select(Payroll)
        .where(Payroll.tenant_id == tenant_id, Payroll.number.like(f"{prefix}%"))
        .order_by(Payroll.number.desc())
        .limit(1)
    )

    result = db.execute(stmt)
    last_nomina = result.scalar_one_or_none()

    if last_nomina and last_nomina.number:
        try:
            last_num = int(last_nomina.number.split("-")[-1])
            next_num = last_num + 1
        except (ValueError, IndexError):
            next_num = 1
    else:
        next_num = 1

    return f"{prefix}{next_num:04d}"


def _calculate_seg_social(base_cotizacion: Decimal, country: str) -> tuple[Decimal, Decimal]:
    """
    Calcula cotización seguridad social según país.
    Retorna (importe, tasa)
    """
    if country == "ES":
        # España: ~6.35% empleado (simplificado)
        rate = Decimal("0.0635")
    elif country == "EC":
        # Ecuador: 9.45% empleado para IESS
        rate = Decimal("0.0945")
    else:
        rate = Decimal("0")

    importe = (base_cotizacion * rate).quantize(Decimal("0.01"))
    return importe, rate


def _calculate_irpf(base_irpf: Decimal, country: str) -> tuple[Decimal, Decimal]:
    """
    Calcula retención IRPF/IR según país.
    Retorna (importe, tasa)

    NOTA: Implementación simplificada. En producción debe usar
    tablas de tramos fiscales actualizadas.
    """
    if country == "ES":
        # España: Tabla simplificada IRPF 2024
        if base_irpf <= 12450:
            rate = Decimal("0.19")
        elif base_irpf <= 20200:
            rate = Decimal("0.24")
        elif base_irpf <= 35200:
            rate = Decimal("0.30")
        elif base_irpf <= 60000:
            rate = Decimal("0.37")
        else:
            rate = Decimal("0.45")

    elif country == "EC":
        # Ecuador: Tabla simplificada IR 2024
        if base_irpf <= 11722:
            rate = Decimal("0")
        elif base_irpf <= 14930:
            rate = Decimal("0.05")
        elif base_irpf <= 19385:
            rate = Decimal("0.10")
        elif base_irpf <= 25638:
            rate = Decimal("0.12")
        else:
            rate = Decimal("0.15")
    else:
        rate = Decimal("0")

    importe = (base_irpf * rate).quantize(Decimal("0.01"))
    return importe, rate


def _calculate_totals(
    payroll_data: dict, concepts: list[PayrollConceptCreate], country: str
) -> dict:
    """Calculate all payroll totals"""
    base_salary = payroll_data.get("base_salary", Decimal("0"))
    allowances = payroll_data.get("allowances", Decimal("0"))
    overtime = payroll_data.get("overtime", payroll_data.get("overtime_hours", Decimal("0")))
    other_earnings = payroll_data.get("other_earnings", Decimal("0"))

    concept_earnings = (
        sum(c.amount for c in concepts if c.concept_type == "EARNING") if concepts else Decimal("0")
    )

    total_earnings = base_salary + allowances + overtime + other_earnings + concept_earnings

    contribution_base = (
        base_salary
        + allowances
        + overtime
        + sum(
            c.amount
            for c in concepts
            if c.concept_type == "EARNING" and getattr(c, "is_base", True)
        )
        if concepts
        else base_salary + allowances + overtime
    )

    social_security, social_security_rate = _calculate_seg_social(contribution_base, country)
    income_tax, income_tax_rate = _calculate_irpf(contribution_base, country)

    other_deductions = payroll_data.get("other_deductions", Decimal("0"))
    concept_deductions = (
        sum(c.amount for c in concepts if c.concept_type == "DEDUCTION")
        if concepts
        else Decimal("0")
    )

    total_deductions = social_security + income_tax + other_deductions + concept_deductions
    net_total = total_earnings - total_deductions

    return {
        "total_earnings": total_earnings,
        "contribution_base": contribution_base,
        "social_security": social_security,
        "social_security_rate": social_security_rate,
        "income_tax": income_tax,
        "income_tax_rate": income_tax_rate,
        "total_deductions": total_deductions,
        "net_total": net_total,
    }


# ============================================================================
# ENDPOINTS - EMPLEADOS
# ============================================================================


@router.get(
    "/employees",
    response_model=EmpleadoList,
    summary="Listar empleados",
    description="Lista paginada de empleados con filtros opcionales",
)
def list_empleados(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: str | None = None,
    activo: bool | None = None,
    departamento: str | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """
    Lista paginada de empleados con filtros.

    **Filtros:**
    - search: Buscar por nombre, apellido, email o cédula
    - activo: Filtrar por estado activo/inactivo
    - departamento: Filtrar por departamento
    """
    tenant_id = UUID(claims["tenant_id"])
    query = db.query(Empleado).filter(Empleado.tenant_id == tenant_id)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Empleado.name.ilike(search_filter))
            | (Empleado.apellido.ilike(search_filter))
            | (Empleado.email.ilike(search_filter))
            | (Empleado.cedula.ilike(search_filter))
        )

    if activo is not None:
        query = query.filter(Empleado.active == activo)

    if departamento:
        query = query.filter(Empleado.departamento == departamento)

    total = query.count()
    empleados = query.order_by(Empleado.apellido, Empleado.name).offset(skip).limit(limit).all()

    return EmpleadoList(
        items=empleados,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/employees",
    response_model=EmpleadoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear empleado",
)
def create_empleado(
    empleado_in: EmpleadoCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Crear nuevo empleado"""
    tenant_id = UUID(claims["tenant_id"])
    user_id = UUID(claims["user_id"])

    # Verificar duplicado por cédula
    existing = (
        db.query(Empleado)
        .filter(and_(Empleado.tenant_id == tenant_id, Empleado.cedula == empleado_in.cedula))
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un empleado con esta cédula",
        )

    empleado = Empleado(
        tenant_id=tenant_id,
        nombre=empleado_in.name,
        apellido=empleado_in.apellido,
        cedula=empleado_in.cedula,
        email=empleado_in.email,
        telefono=empleado_in.phone,
        fecha_ingreso=empleado_in.fecha_ingreso,
        cargo=empleado_in.cargo,
        departamento=empleado_in.departamento,
        salario=empleado_in.salario,
        activo=empleado_in.active if empleado_in.active is not None else True,
        direccion=empleado_in.address,
        ciudad=empleado_in.city,
        created_by=user_id,
    )

    db.add(empleado)
    db.commit()
    db.refresh(empleado)
    return empleado


@router.get(
    "/employees/{id}",
    response_model=EmpleadoResponse,
    summary="Obtener empleado",
)
def get_empleado(
    id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Obtener detalle de un empleado"""
    tenant_id = UUID(claims["tenant_id"])

    empleado = (
        db.query(Empleado).filter(and_(Empleado.id == id, Empleado.tenant_id == tenant_id)).first()
    )

    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    return empleado


@router.put(
    "/employees/{id}",
    response_model=EmpleadoResponse,
    summary="Actualizar empleado",
)
def update_empleado(
    id: UUID,
    empleado_in: EmpleadoUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Actualizar datos de un empleado"""
    tenant_id = UUID(claims["tenant_id"])
    user_id = UUID(claims["user_id"])

    empleado = (
        db.query(Empleado).filter(and_(Empleado.id == id, Empleado.tenant_id == tenant_id)).first()
    )

    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    update_data = empleado_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(empleado, field, value)

    empleado.updated_by = user_id

    db.commit()
    db.refresh(empleado)
    return empleado


@router.delete(
    "/employees/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar empleado",
)
def delete_empleado(
    id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Eliminar empleado (desactivar)"""
    tenant_id = UUID(claims["tenant_id"])
    user_id = UUID(claims["user_id"])

    empleado = (
        db.query(Empleado).filter(and_(Empleado.id == id, Empleado.tenant_id == tenant_id)).first()
    )

    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    empleado.active = False
    empleado.fecha_salida = datetime.utcnow().date()
    empleado.updated_by = user_id

    db.commit()


# ============================================================================
# ENDPOINTS - VACACIONES
# ============================================================================


@router.get(
    "/vacations",
    response_model=VacacionList,
    summary="Listar vacaciones",
)
def list_vacaciones(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    empleado_id: UUID | None = None,
    estado: str | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Lista paginada de solicitudes de vacaciones"""
    tenant_id = UUID(claims["tenant_id"])

    query = db.query(Vacacion).filter(Vacacion.tenant_id == tenant_id)

    if empleado_id:
        query = query.filter(Vacacion.empleado_id == empleado_id)

    if estado:
        query = query.filter(Vacacion.estado == estado)

    total = query.count()
    vacaciones = query.order_by(Vacacion.fecha_inicio.desc()).offset(skip).limit(limit).all()

    return VacacionList(
        items=vacaciones,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
    )


@router.post(
    "/vacations",
    response_model=VacacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear solicitud de vacaciones",
)
def create_vacacion(
    vacacion_in: VacacionCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Crear solicitud de vacaciones"""
    tenant_id = UUID(claims["tenant_id"])
    user_id = UUID(claims["user_id"])

    # Validar que empleado existe y está activo
    empleado = (
        db.query(Empleado)
        .filter(and_(Empleado.id == vacacion_in.empleado_id, Empleado.tenant_id == tenant_id))
        .first()
    )

    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    if not empleado.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="El empleado no está activo"
        )

    dias = (vacacion_in.fecha_fin - vacacion_in.fecha_inicio).days + 1

    vacacion = Vacacion(
        tenant_id=tenant_id,
        empleado_id=vacacion_in.empleado_id,
        fecha_inicio=vacacion_in.fecha_inicio,
        fecha_fin=vacacion_in.fecha_fin,
        dias=dias,
        tipo=vacacion_in.tipo or "vacaciones",
        estado="pendiente",
        motivo=vacacion_in.motivo,
        created_by=user_id,
    )

    db.add(vacacion)
    db.commit()
    db.refresh(vacacion)
    return vacacion


@router.get(
    "/vacations/{id}",
    response_model=VacacionResponse,
    summary="Obtener vacación",
)
def get_vacacion(
    id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Obtener detalle de solicitud de vacaciones"""
    tenant_id = UUID(claims["tenant_id"])

    vacacion = (
        db.query(Vacacion).filter(and_(Vacacion.id == id, Vacacion.tenant_id == tenant_id)).first()
    )

    if not vacacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud de vacaciones no encontrada",
        )

    return vacacion


@router.put(
    "/vacations/{id}/approve",
    response_model=VacacionResponse,
    summary="Aprobar vacación",
)
def aprobar_vacacion(
    id: UUID,
    observaciones: str | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Aprobar solicitud de vacaciones"""
    tenant_id = UUID(claims["tenant_id"])
    user_id = UUID(claims["user_id"])

    vacacion = (
        db.query(Vacacion).filter(and_(Vacacion.id == id, Vacacion.tenant_id == tenant_id)).first()
    )

    if not vacacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud de vacaciones no encontrada",
        )

    if vacacion.estado != "pendiente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden aprobar solicitudes pendientes",
        )

    vacacion.estado = "aprobado"
    vacacion.aprobado_por = user_id
    vacacion.fecha_aprobacion = datetime.utcnow()
    vacacion.observaciones = observaciones
    vacacion.updated_by = user_id

    db.commit()
    db.refresh(vacacion)
    return vacacion


@router.put(
    "/vacations/{id}/reject",
    response_model=VacacionResponse,
    summary="Rechazar vacación",
)
def rechazar_vacacion(
    id: UUID,
    motivo_rechazo: str = Query(..., description="Motivo del rechazo"),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Rechazar solicitud de vacaciones"""
    tenant_id = UUID(claims["tenant_id"])
    user_id = UUID(claims["user_id"])

    vacacion = (
        db.query(Vacacion).filter(and_(Vacacion.id == id, Vacacion.tenant_id == tenant_id)).first()
    )

    if not vacacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud de vacaciones no encontrada",
        )

    if vacacion.estado != "pendiente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden rechazar solicitudes pendientes",
        )

    vacacion.estado = "rechazado"
    vacacion.aprobado_por = user_id
    vacacion.fecha_aprobacion = datetime.utcnow()
    vacacion.observaciones = motivo_rechazo
    vacacion.updated_by = user_id

    db.commit()
    db.refresh(vacacion)
    return vacacion


@router.delete(
    "/vacations/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar vacación",
)
def delete_vacacion(
    id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Eliminar solicitud de vacaciones (solo si está pendiente)"""
    tenant_id = UUID(claims["tenant_id"])

    vacacion = (
        db.query(Vacacion).filter(and_(Vacacion.id == id, Vacacion.tenant_id == tenant_id)).first()
    )

    if not vacacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud de vacaciones no encontrada",
        )

    if vacacion.estado != "pendiente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo se pueden eliminar solicitudes pendientes",
        )

    db.delete(vacacion)
    db.commit()


# ============================================================================
# ENDPOINTS - NÓMINAS
# ============================================================================


@router.get(
    "/payroll",
    response_model=PayrollList,
    summary="Listar nóminas",
)
async def list_nominas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    employee_id: UUID | None = None,
    period_month: int | None = Query(None, ge=1, le=12),
    period_year: int | None = Query(None, ge=2020, le=2100),
    status: str | None = Query(None, pattern="^(DRAFT|APPROVED|PAID|CANCELLED)$"),
    payroll_type: str | None = Query(None, pattern="^(MONTHLY|BONUS|SEVERANCE|SPECIAL)$"),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """
    Lista todas las nóminas con filtros opcionales.

    **Filtros:**
    - empleado_id: Filtrar por empleado
    - period_month: Mes del período
    - period_year: Año del período
    - status: Estado de la nómina (DRAFT, APPROVED, PAID, CANCELLED)
    - payroll_type: Tipo de nómina (MONTHLY, BONUS, SEVERANCE, SPECIAL)
    """
    tenant_id = claims["tenant_id"]

    stmt = select(Payroll).where(Payroll.tenant_id == tenant_id)

    if employee_id:
        stmt = stmt.where(Payroll.employee_id == employee_id)
    if period_month:
        stmt = stmt.where(Payroll.period_month == period_month)
    if period_year:
        stmt = stmt.where(Payroll.period_year == period_year)
    if status:
        stmt = stmt.where(Payroll.status == status)
    if payroll_type:
        stmt = stmt.where(Payroll.type == payroll_type)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    stmt = (
        stmt.order_by(
            Payroll.period_year.desc(), Payroll.period_month.desc(), Payroll.number.desc()
        )
        .offset(skip)
        .limit(limit)
    )

    result = db.execute(stmt)
    nominas = result.scalars().all()

    return PayrollList(
        items=[PayrollResponse.from_orm(n) for n in nominas],
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=ceil(total / limit) if total > 0 else 0,
    )


@router.post(
    "/payroll",
    response_model=PayrollResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nómina",
)
async def create_nomina(
    data: PayrollCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """
    Crea una nueva nómina.

    Si auto_calculate=True (por defecto):
    - Calcula automáticamente Seg. Social e IRPF/IR
    - Calcula totales devengado, deducido y líquido
    """
    tenant_id = claims["tenant_id"]
    user_id = claims["user_id"]

    # Validar empleado
    stmt = select(Empleado).where(
        Empleado.id == data.employee_id, Empleado.tenant_id == tenant_id, Empleado.activo
    )
    empleado = db.execute(stmt).scalar_one_or_none()

    if not empleado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado o inactivo"
        )

    # Validar duplicado
    stmt = select(Payroll).where(
        Payroll.tenant_id == tenant_id,
        Payroll.employee_id == data.employee_id,
        Payroll.period_month == data.period_month,
        Payroll.period_year == data.period_year,
        Payroll.type == data.payroll_type,
        Payroll.status != "CANCELLED",
    )
    existing = db.execute(stmt).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una nómina {data.payroll_type} para este empleado en {data.period_month}/{data.period_year}",
        )

    numero = _generate_numero_nomina(db, tenant_id, data.period_month, data.period_year)

    # Obtener país del tenant
    country = _get_tenant_country(db, tenant_id)

    nomina_dict = data.dict(exclude={"concepts", "auto_calculate"})
    # Map schema fields to model fields
    if "overtime_hours" in nomina_dict:
        nomina_dict["overtime"] = nomina_dict.pop("overtime_hours")
    if "payroll_type" in nomina_dict:
        nomina_dict["type"] = nomina_dict.pop("payroll_type")

    if data.auto_calculate:
        calcs = _calculate_totals(nomina_dict, data.concepts or [], country)
        nomina_dict.update(
            {
                "total_earnings": calcs["total_earnings"],
                "social_security": calcs["social_security"],
                "income_tax": calcs["income_tax"],
                "total_deductions": calcs["total_deductions"],
                "net_total": calcs["net_total"],
            }
        )
    else:
        nomina_dict["total_earnings"] = (
            nomina_dict["base_salary"]
            + nomina_dict["allowances"]
            + nomina_dict["overtime"]
            + nomina_dict["other_earnings"]
        )
        nomina_dict["total_deductions"] = (
            nomina_dict["social_security"]
            + nomina_dict["income_tax"]
            + nomina_dict["other_deductions"]
        )
        nomina_dict["net_total"] = nomina_dict["total_earnings"] - nomina_dict["total_deductions"]

    nomina = Payroll(
        tenant_id=tenant_id, number=numero, status="DRAFT", created_by=user_id, **nomina_dict
    )

    db.add(nomina)
    db.flush()

    if data.concepts:
        for concepto_data in data.concepts:
            concepto = PayrollConcept(payroll_id=nomina.id, **concepto_data.dict())
            db.add(concepto)

    db.commit()
    db.refresh(nomina)

    return PayrollResponse.from_orm(nomina)


@router.get(
    "/payroll/{nomina_id}",
    response_model=PayrollResponse,
    summary="Obtener nómina",
)
async def get_nomina(
    nomina_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Obtiene detalle de una nómina"""
    tenant_id = claims["tenant_id"]

    stmt = select(Payroll).where(Payroll.id == nomina_id, Payroll.tenant_id == tenant_id)
    nomina = db.execute(stmt).scalar_one_or_none()

    if not nomina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nómina no encontrada")

    return PayrollResponse.from_orm(nomina)


@router.put(
    "/payroll/{nomina_id}",
    response_model=PayrollResponse,
    summary="Actualizar nómina",
)
async def update_nomina(
    nomina_id: UUID,
    data: PayrollUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Actualiza una nómina (solo si está en DRAFT)"""
    tenant_id = claims["tenant_id"]

    stmt = select(Payroll).where(Payroll.id == nomina_id, Payroll.tenant_id == tenant_id)
    nomina = db.execute(stmt).scalar_one_or_none()

    if not nomina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nómina no encontrada")

    if nomina.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden editar nóminas en estado DRAFT",
        )

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        target = "overtime" if key == "overtime_hours" else key
        setattr(nomina, target, value)

    # Recalcular totales
    nomina.total_earnings = (
        nomina.base_salary + nomina.allowances + nomina.overtime + nomina.other_earnings
    )
    nomina.total_deductions = nomina.social_security + nomina.income_tax + nomina.other_deductions
    nomina.net_total = nomina.total_earnings - nomina.total_deductions

    db.commit()
    db.refresh(nomina)

    return PayrollResponse.from_orm(nomina)


@router.delete(
    "/payroll/{nomina_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar nómina",
)
async def delete_nomina(
    nomina_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Elimina una nómina (solo si está en DRAFT)"""
    tenant_id = claims["tenant_id"]

    stmt = select(Payroll).where(Payroll.id == nomina_id, Payroll.tenant_id == tenant_id)
    nomina = db.execute(stmt).scalar_one_or_none()

    if not nomina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nómina no encontrada")

    if nomina.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden eliminar nóminas en estado DRAFT",
        )

    db.delete(nomina)
    db.commit()


@router.post(
    "/payroll/{nomina_id}/approve",
    response_model=PayrollResponse,
    summary="Aprobar nómina",
)
async def approve_nomina(
    nomina_id: UUID,
    data: PayrollApproveRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Aprueba una nómina (DRAFT → APPROVED)"""
    tenant_id = claims["tenant_id"]
    user_id = claims["user_id"]

    stmt = select(Payroll).where(Payroll.id == nomina_id, Payroll.tenant_id == tenant_id)
    nomina = db.execute(stmt).scalar_one_or_none()

    if not nomina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nómina no encontrada")

    if nomina.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden aprobar nóminas en estado DRAFT",
        )

    nomina.status = "APPROVED"
    nomina.approved_by = user_id
    nomina.approved_at = datetime.utcnow()

    if data.notes:
        nomina.notes = (nomina.notes or "") + f"\n[APPROVAL] {data.notes}"

    db.commit()
    db.refresh(nomina)

    return PayrollResponse.from_orm(nomina)


@router.post(
    "/payroll/{nomina_id}/pay",
    response_model=PayrollResponse,
    summary="Pagar nómina",
)
async def pay_nomina(
    nomina_id: UUID,
    data: PayrollPayRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Marca una nómina como pagada (APPROVED → PAID)"""
    tenant_id = claims["tenant_id"]

    stmt = select(Payroll).where(Payroll.id == nomina_id, Payroll.tenant_id == tenant_id)
    nomina = db.execute(stmt).scalar_one_or_none()

    if not nomina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nómina no encontrada")

    if nomina.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden pagar nóminas en estado APPROVED",
        )

    nomina.status = "PAID"
    nomina.payment_date = data.payment_date
    nomina.payment_method = data.payment_method

    if data.payment_reference:
        nomina.notes = (nomina.notes or "") + f"\n[PAYMENT] Ref: {data.payment_reference}"

    db.commit()
    db.refresh(nomina)

    return PayrollResponse.from_orm(nomina)


@router.post(
    "/payroll/calculate",
    response_model=PayrollCalculateResponse,
    summary="Calcular nómina",
)
async def calculate_nomina(
    data: PayrollCalculateRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """
    Calculadora de nómina.

    Calcula automáticamente devengos, deducciones y líquido total
    sin crear la nómina. Útil para planificación.
    """
    tenant_id = claims["tenant_id"]

    stmt = select(Empleado).where(Empleado.id == data.employee_id, Empleado.tenant_id == tenant_id)
    empleado = db.execute(stmt).scalar_one_or_none()

    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    salario_base = data.base_salary or empleado.salario_base or Decimal("0")
    allowances = data.allowances or Decimal("0")
    overtime = data.overtime_hours or Decimal("0")
    other_earnings = data.other_earnings or Decimal("0")

    nomina_dict = {
        "base_salary": salario_base,
        "allowances": allowances,
        "overtime_hours": overtime,
        "other_earnings": other_earnings,
        "other_deductions": Decimal("0"),
    }

    # Obtener país del tenant
    country = _get_tenant_country(db, tenant_id)
    calcs = _calculate_totals(nomina_dict, data.concepts or [], country)

    return PayrollCalculateResponse(
        employee_id=data.employee_id,
        period_month=data.period_month,
        period_year=data.period_year,
        payroll_type=data.payroll_type,
        base_salary=salario_base,
        allowances=allowances,
        overtime_hours=overtime,
        other_earnings=other_earnings,
        total_earnings=calcs["total_earnings"],
        social_security=calcs["social_security"],
        social_security_rate=calcs["social_security_rate"],
        income_tax=calcs["income_tax"],
        income_tax_rate=calcs["income_tax_rate"],
        other_deductions=Decimal("0"),
        total_deductions=calcs["total_deductions"],
        net_total=calcs["net_total"],
        contribution_base=calcs["contribution_base"],
        income_tax_base=calcs["contribution_base"],
        concepts_detail=[c.dict() for c in (data.concepts or [])],
        employee_name=f"{empleado.nombre} {empleado.apellidos or ''}".strip(),
        employee_role=empleado.cargo,
    )


@router.get(
    "/payroll/stats",
    response_model=PayrollStats,
    summary="Estadísticas de nóminas",
)
async def get_nominas_stats(
    period_month: int | None = Query(None, ge=1, le=12),
    period_year: int | None = Query(None, ge=2020, le=2100),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """
    Estadísticas de nóminas.

    Si no se especifica período, usa el mes/año actual.
    """
    tenant_id = claims["tenant_id"]

    now = datetime.utcnow()
    mes = period_month or now.month
    ano = period_year or now.year

    stmt = select(Payroll).where(
        Payroll.tenant_id == tenant_id, Payroll.period_month == mes, Payroll.period_year == ano
    )

    total_draft = db.execute(
        select(func.count()).select_from(stmt.where(Payroll.status == "DRAFT").subquery())
    ).scalar_one()

    total_approved = db.execute(
        select(func.count()).select_from(stmt.where(Payroll.status == "APPROVED").subquery())
    ).scalar_one()

    total_paid = db.execute(
        select(func.count()).select_from(stmt.where(Payroll.status == "PAID").subquery())
    ).scalar_one()

    total_cancelled = db.execute(
        select(func.count()).select_from(stmt.where(Payroll.status == "CANCELLED").subquery())
    ).scalar_one()

    result = db.execute(
        select(
            func.sum(Payroll.total_earnings),
            func.sum(Payroll.total_deductions),
            func.sum(Payroll.net_total),
            func.avg(Payroll.net_total),
        ).select_from(stmt.subquery())
    ).one()

    total_devengado_mes = result[0] or Decimal("0")
    total_deducido_mes = result[1] or Decimal("0")
    total_liquido_mes = result[2] or Decimal("0")
    promedio_liquido = result[3] or Decimal("0")

    total_nominas = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    total_empleados = db.execute(
        select(func.count(func.distinct(Payroll.employee_id))).select_from(stmt.subquery())
    ).scalar_one()

    payrolls_by_type = {}
    for tipo in ["MONTHLY", "BONUS", "SEVERANCE", "SPECIAL"]:
        count = db.execute(
            select(func.count()).select_from(stmt.where(Payroll.type == tipo).subquery())
        ).scalar_one()
        payrolls_by_type[tipo] = count

    return PayrollStats(
        total_draft=total_draft,
        total_approved=total_approved,
        total_paid=total_paid,
        total_cancelled=total_cancelled,
        total_earnings_mes=total_devengado_mes,
        total_deductions_mes=total_deducido_mes,
        total_liquido_mes=total_liquido_mes,
        promedio_liquido=promedio_liquido,
        payrolls_by_type=payrolls_by_type,
        period_month=mes,
        period_year=ano,
        total_empleados=total_empleados,
        total_payrolls=total_nominas,
    )
