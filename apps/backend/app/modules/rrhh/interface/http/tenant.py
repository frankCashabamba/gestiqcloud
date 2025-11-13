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

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls

# Models
from app.models.hr import Empleado, Vacacion
from app.models.hr.nomina import Nomina, NominaConcepto

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

# Schemas - Nóminas
from app.schemas.hr_nomina import (
    NominaApproveRequest,
    NominaCalculateRequest,
    NominaCalculateResponse,
    NominaConceptoCreate,
    NominaCreate,
    NominaList,
    NominaPayRequest,
    NominaResponse,
    NominaStats,
    NominaUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

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


def _generate_numero_nomina(db: Session, tenant_id: UUID, mes: int, ano: int) -> str:
    """Genera número único de nómina: NOM-YYYY-MM-NNNN"""
    prefix = f"NOM-{ano}-{mes:02d}-"

    stmt = (
        select(Nomina)
        .where(Nomina.tenant_id == tenant_id, Nomina.numero.like(f"{prefix}%"))
        .order_by(Nomina.numero.desc())
        .limit(1)
    )

    result = db.execute(stmt)
    last_nomina = result.scalar_one_or_none()

    if last_nomina and last_nomina.numero:
        try:
            last_num = int(last_nomina.numero.split("-")[-1])
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
    nomina_data: dict, conceptos: list[NominaConceptoCreate], country: str
) -> dict:
    """Calcula todos los totales de la nómina"""
    salario_base = nomina_data.get("salario_base", Decimal("0"))
    complementos = nomina_data.get("complementos", Decimal("0"))
    horas_extra = nomina_data.get("horas_extra", Decimal("0"))
    otros_devengos = nomina_data.get("otros_devengos", Decimal("0"))

    devengos_conceptos = (
        sum(c.importe for c in conceptos if c.tipo == "DEVENGO") if conceptos else Decimal("0")
    )

    total_devengado = (
        salario_base + complementos + horas_extra + otros_devengos + devengos_conceptos
    )

    base_cotizacion = (
        salario_base
        + complementos
        + horas_extra
        + sum(c.importe for c in conceptos if c.tipo == "DEVENGO" and c.es_base)
        if conceptos
        else salario_base + complementos + horas_extra
    )

    seg_social, seg_social_rate = _calculate_seg_social(base_cotizacion, country)
    irpf, irpf_rate = _calculate_irpf(base_cotizacion, country)

    otras_deducciones = nomina_data.get("otras_deducciones", Decimal("0"))
    deducciones_conceptos = (
        sum(c.importe for c in conceptos if c.tipo == "DEDUCCION") if conceptos else Decimal("0")
    )

    total_deducido = seg_social + irpf + otras_deducciones + deducciones_conceptos
    liquido_total = total_devengado - total_deducido

    return {
        "total_devengado": total_devengado,
        "base_cotizacion": base_cotizacion,
        "seg_social": seg_social,
        "seg_social_rate": seg_social_rate,
        "irpf": irpf,
        "irpf_rate": irpf_rate,
        "total_deducido": total_deducido,
        "liquido_total": liquido_total,
    }


# ============================================================================
# ENDPOINTS - EMPLEADOS
# ============================================================================


@router.get(
    "/empleados",
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
    "/empleados",
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
    "/empleados/{id}",
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
    "/empleados/{id}",
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
    "/empleados/{id}",
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
    "/vacaciones",
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
    "/vacaciones",
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
    "/vacaciones/{id}",
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
    "/vacaciones/{id}/aprobar",
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
    "/vacaciones/{id}/rechazar",
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
    "/vacaciones/{id}",
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
    "/nominas",
    response_model=NominaList,
    summary="Listar nóminas",
)
async def list_nominas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    empleado_id: UUID | None = None,
    periodo_mes: int | None = Query(None, ge=1, le=12),
    periodo_ano: int | None = Query(None, ge=2020, le=2100),
    status: str | None = Query(None, regex="^(DRAFT|APPROVED|PAID|CANCELLED)$"),
    tipo: str | None = Query(None, regex="^(MENSUAL|EXTRA|FINIQUITO|ESPECIAL)$"),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """
    Lista todas las nóminas con filtros opcionales.

    **Filtros:**
    - empleado_id: Filtrar por empleado
    - periodo_mes: Mes del período
    - periodo_ano: Año del período
    - status: Estado de la nómina (DRAFT, APPROVED, PAID, CANCELLED)
    - tipo: Tipo de nómina (MENSUAL, EXTRA, FINIQUITO, ESPECIAL)
    """
    tenant_id = claims["tenant_id"]

    stmt = select(Nomina).where(Nomina.tenant_id == tenant_id)

    if empleado_id:
        stmt = stmt.where(Nomina.empleado_id == empleado_id)
    if periodo_mes:
        stmt = stmt.where(Nomina.periodo_mes == periodo_mes)
    if periodo_ano:
        stmt = stmt.where(Nomina.periodo_ano == periodo_ano)
    if status:
        stmt = stmt.where(Nomina.status == status)
    if tipo:
        stmt = stmt.where(Nomina.tipo == tipo)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    stmt = (
        stmt.order_by(Nomina.periodo_ano.desc(), Nomina.periodo_mes.desc(), Nomina.numero.desc())
        .offset(skip)
        .limit(limit)
    )

    result = db.execute(stmt)
    nominas = result.scalars().all()

    return NominaList(
        items=[NominaResponse.from_orm(n) for n in nominas],
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=ceil(total / limit) if total > 0 else 0,
    )


@router.post(
    "/nominas",
    response_model=NominaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nómina",
)
async def create_nomina(
    data: NominaCreate,
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
        Empleado.id == data.empleado_id, Empleado.tenant_id == tenant_id, Empleado.activo == True
    )
    empleado = db.execute(stmt).scalar_one_or_none()

    if not empleado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado o inactivo"
        )

    # Validar duplicado
    stmt = select(Nomina).where(
        Nomina.tenant_id == tenant_id,
        Nomina.empleado_id == data.empleado_id,
        Nomina.periodo_mes == data.periodo_mes,
        Nomina.periodo_ano == data.periodo_ano,
        Nomina.tipo == data.tipo,
        Nomina.status != "CANCELLED",
    )
    existing = db.execute(stmt).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una nómina {data.tipo} para este empleado en {data.periodo_mes}/{data.periodo_ano}",
        )

    numero = _generate_numero_nomina(db, tenant_id, data.periodo_mes, data.periodo_ano)

    # TODO: Obtener país del tenant
    country = "ES"

    nomina_dict = data.dict(exclude={"conceptos", "auto_calculate"})

    if data.auto_calculate:
        calcs = _calculate_totals(nomina_dict, data.conceptos or [], country)
        nomina_dict.update(
            {
                "total_devengado": calcs["total_devengado"],
                "seg_social": calcs["seg_social"],
                "irpf": calcs["irpf"],
                "total_deducido": calcs["total_deducido"],
                "liquido_total": calcs["liquido_total"],
            }
        )
    else:
        nomina_dict["total_devengado"] = (
            nomina_dict["salario_base"]
            + nomina_dict["complementos"]
            + nomina_dict["horas_extra"]
            + nomina_dict["otros_devengos"]
        )
        nomina_dict["total_deducido"] = (
            nomina_dict["seg_social"] + nomina_dict["irpf"] + nomina_dict["otras_deducciones"]
        )
        nomina_dict["liquido_total"] = (
            nomina_dict["total_devengado"] - nomina_dict["total_deducido"]
        )

    nomina = Nomina(
        tenant_id=tenant_id, numero=numero, status="DRAFT", created_by=user_id, **nomina_dict
    )

    db.add(nomina)
    db.flush()

    if data.conceptos:
        for concepto_data in data.conceptos:
            concepto = NominaConcepto(nomina_id=nomina.id, **concepto_data.dict())
            db.add(concepto)

    db.commit()
    db.refresh(nomina)

    return NominaResponse.from_orm(nomina)


@router.get(
    "/nominas/{nomina_id}",
    response_model=NominaResponse,
    summary="Obtener nómina",
)
async def get_nomina(
    nomina_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Obtiene detalle de una nómina"""
    tenant_id = claims["tenant_id"]

    stmt = select(Nomina).where(Nomina.id == nomina_id, Nomina.tenant_id == tenant_id)
    nomina = db.execute(stmt).scalar_one_or_none()

    if not nomina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nómina no encontrada")

    return NominaResponse.from_orm(nomina)


@router.put(
    "/nominas/{nomina_id}",
    response_model=NominaResponse,
    summary="Actualizar nómina",
)
async def update_nomina(
    nomina_id: UUID,
    data: NominaUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Actualiza una nómina (solo si está en DRAFT)"""
    tenant_id = claims["tenant_id"]

    stmt = select(Nomina).where(Nomina.id == nomina_id, Nomina.tenant_id == tenant_id)
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
        setattr(nomina, key, value)

    # Recalcular totales
    nomina.total_devengado = (
        nomina.salario_base + nomina.complementos + nomina.horas_extra + nomina.otros_devengos
    )
    nomina.total_deducido = nomina.seg_social + nomina.irpf + nomina.otras_deducciones
    nomina.liquido_total = nomina.total_devengado - nomina.total_deducido

    db.commit()
    db.refresh(nomina)

    return NominaResponse.from_orm(nomina)


@router.delete(
    "/nominas/{nomina_id}",
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

    stmt = select(Nomina).where(Nomina.id == nomina_id, Nomina.tenant_id == tenant_id)
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
    "/nominas/{nomina_id}/approve",
    response_model=NominaResponse,
    summary="Aprobar nómina",
)
async def approve_nomina(
    nomina_id: UUID,
    data: NominaApproveRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Aprueba una nómina (DRAFT → APPROVED)"""
    tenant_id = claims["tenant_id"]
    user_id = claims["user_id"]

    stmt = select(Nomina).where(Nomina.id == nomina_id, Nomina.tenant_id == tenant_id)
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

    if data.notas:
        nomina.notas = (nomina.notas or "") + f"\n[APROBACIÓN] {data.notas}"

    db.commit()
    db.refresh(nomina)

    return NominaResponse.from_orm(nomina)


@router.post(
    "/nominas/{nomina_id}/pay",
    response_model=NominaResponse,
    summary="Pagar nómina",
)
async def pay_nomina(
    nomina_id: UUID,
    data: NominaPayRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Marca una nómina como pagada (APPROVED → PAID)"""
    tenant_id = claims["tenant_id"]

    stmt = select(Nomina).where(Nomina.id == nomina_id, Nomina.tenant_id == tenant_id)
    nomina = db.execute(stmt).scalar_one_or_none()

    if not nomina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nómina no encontrada")

    if nomina.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden pagar nóminas en estado APPROVED",
        )

    nomina.status = "PAID"
    nomina.fecha_pago = data.fecha_pago
    nomina.metodo_pago = data.metodo_pago

    if data.referencia_pago:
        nomina.notas = (nomina.notas or "") + f"\n[PAGO] Ref: {data.referencia_pago}"

    db.commit()
    db.refresh(nomina)

    return NominaResponse.from_orm(nomina)


@router.post(
    "/nominas/calculate",
    response_model=NominaCalculateResponse,
    summary="Calcular nómina",
)
async def calculate_nomina(
    data: NominaCalculateRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """
    Calculadora de nómina.

    Calcula automáticamente devengos, deducciones y líquido total
    sin crear la nómina. Útil para planificación.
    """
    tenant_id = claims["tenant_id"]

    stmt = select(Empleado).where(Empleado.id == data.empleado_id, Empleado.tenant_id == tenant_id)
    empleado = db.execute(stmt).scalar_one_or_none()

    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    salario_base = data.salario_base or empleado.salario_base or Decimal("0")
    complementos = data.complementos or Decimal("0")
    horas_extra = data.horas_extra or Decimal("0")
    otros_devengos = data.otros_devengos or Decimal("0")

    nomina_dict = {
        "salario_base": salario_base,
        "complementos": complementos,
        "horas_extra": horas_extra,
        "otros_devengos": otros_devengos,
        "otras_deducciones": Decimal("0"),
    }

    country = "ES"  # TODO: obtener del tenant
    calcs = _calculate_totals(nomina_dict, data.conceptos or [], country)

    return NominaCalculateResponse(
        empleado_id=data.empleado_id,
        periodo_mes=data.periodo_mes,
        periodo_ano=data.periodo_ano,
        tipo=data.tipo,
        salario_base=salario_base,
        complementos=complementos,
        horas_extra=horas_extra,
        otros_devengos=otros_devengos,
        total_devengado=calcs["total_devengado"],
        seg_social=calcs["seg_social"],
        seg_social_rate=calcs["seg_social_rate"],
        irpf=calcs["irpf"],
        irpf_rate=calcs["irpf_rate"],
        otras_deducciones=Decimal("0"),
        total_deducido=calcs["total_deducido"],
        liquido_total=calcs["liquido_total"],
        base_cotizacion=calcs["base_cotizacion"],
        base_irpf=calcs["base_cotizacion"],
        conceptos_detalle=[c.dict() for c in (data.conceptos or [])],
        empleado_nombre=f"{empleado.nombre} {empleado.apellidos or ''}".strip(),
        empleado_cargo=empleado.cargo,
    )


@router.get(
    "/nominas/stats",
    response_model=NominaStats,
    summary="Estadísticas de nóminas",
)
async def get_nominas_stats(
    periodo_mes: int | None = Query(None, ge=1, le=12),
    periodo_ano: int | None = Query(None, ge=2020, le=2100),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """
    Estadísticas de nóminas.

    Si no se especifica período, usa el mes/año actual.
    """
    tenant_id = claims["tenant_id"]

    now = datetime.utcnow()
    mes = periodo_mes or now.month
    ano = periodo_ano or now.year

    stmt = select(Nomina).where(
        Nomina.tenant_id == tenant_id, Nomina.periodo_mes == mes, Nomina.periodo_ano == ano
    )

    total_draft = db.execute(
        select(func.count()).select_from(stmt.where(Nomina.status == "DRAFT").subquery())
    ).scalar_one()

    total_approved = db.execute(
        select(func.count()).select_from(stmt.where(Nomina.status == "APPROVED").subquery())
    ).scalar_one()

    total_paid = db.execute(
        select(func.count()).select_from(stmt.where(Nomina.status == "PAID").subquery())
    ).scalar_one()

    total_cancelled = db.execute(
        select(func.count()).select_from(stmt.where(Nomina.status == "CANCELLED").subquery())
    ).scalar_one()

    result = db.execute(
        select(
            func.sum(Nomina.total_devengado),
            func.sum(Nomina.total_deducido),
            func.sum(Nomina.liquido_total),
            func.avg(Nomina.liquido_total),
        ).select_from(stmt.subquery())
    ).one()

    total_devengado_mes = result[0] or Decimal("0")
    total_deducido_mes = result[1] or Decimal("0")
    total_liquido_mes = result[2] or Decimal("0")
    promedio_liquido = result[3] or Decimal("0")

    total_nominas = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    total_empleados = db.execute(
        select(func.count(func.distinct(Nomina.empleado_id))).select_from(stmt.subquery())
    ).scalar_one()

    nominas_por_tipo = {}
    for tipo in ["MENSUAL", "EXTRA", "FINIQUITO", "ESPECIAL"]:
        count = db.execute(
            select(func.count()).select_from(stmt.where(Nomina.tipo == tipo).subquery())
        ).scalar_one()
        nominas_por_tipo[tipo] = count

    return NominaStats(
        total_draft=total_draft,
        total_approved=total_approved,
        total_paid=total_paid,
        total_cancelled=total_cancelled,
        total_devengado_mes=total_devengado_mes,
        total_deducido_mes=total_deducido_mes,
        total_liquido_mes=total_liquido_mes,
        promedio_liquido=promedio_liquido,
        nominas_por_tipo=nominas_por_tipo,
        periodo_mes=mes,
        periodo_ano=ano,
        total_empleados=total_empleados,
        total_nominas=total_nominas,
    )
