"""
Contabilidad Module - HTTP API Tenant Interface

Sistema completo de contabilidad general:
- CRUD plan de cuentas jerárquico
- CRUD asientos contables (libro diario)
- Libro mayor por cuenta
- Balance de situación
- Cuenta de pérdidas y ganancias
- Estadísticas contables

Compatible con PGC España y plan contable Ecuador.

MIGRADO DE:
- app/routers/accounting.py
"""

from datetime import date, datetime
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.accounting.plan_cuentas import AsientoContable, AsientoLinea, PlanCuentas
from app.schemas.accounting import (
    AsientoContableCreate,
    AsientoContableList,
    AsientoContableResponse,
    AsientoContableUpdate,
    PlanCuentasCreate,
    PlanCuentasList,
    PlanCuentasResponse,
    PlanCuentasUpdate,
)

router = APIRouter(
    prefix="/accounting",
    tags=["Contabilidad"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# HELPERS
def _generate_numero_asiento(db: Session, tenant_id: UUID, ano: int) -> str:
    """Genera número único de asiento: ASI-YYYY-NNNN"""
    prefix = f"ASI-{ano}-"
    stmt = (
        select(AsientoContable)
        .where(AsientoContable.tenant_id == tenant_id, AsientoContable.numero.like(f"{prefix}%"))
        .order_by(AsientoContable.numero.desc())
        .limit(1)
    )
    result = db.execute(stmt)
    last_asiento = result.scalar_one_or_none()
    if last_asiento and last_asiento.numero:
        try:
            last_num = int(last_asiento.numero.split("-")[-1])
            next_num = last_num + 1
        except (ValueError, IndexError):
            next_num = 1
    else:
        next_num = 1
    return f"{prefix}{next_num:04d}"


def _recalcular_saldos_cuenta(db: Session, cuenta_id: UUID):
    """Recalcula saldos de una cuenta desde sus líneas contabilizadas"""
    stmt = select(PlanCuentas).where(PlanCuentas.id == cuenta_id)
    cuenta = db.execute(stmt).scalar_one_or_none()
    if not cuenta:
        return
    stmt = (
        select(func.sum(AsientoLinea.debe), func.sum(AsientoLinea.haber))
        .join(AsientoContable)
        .where(AsientoLinea.cuenta_id == cuenta_id, AsientoContable.status == "CONTABILIZADO")
    )
    result = db.execute(stmt).one()
    debe = result[0] or Decimal("0")
    haber = result[1] or Decimal("0")
    cuenta.saldo_debe = debe
    cuenta.saldo_haber = haber
    cuenta.saldo = debe - haber


@router.get("/plan-cuentas", response_model=PlanCuentasList)
async def list_cuentas(
    nivel: int | None = Query(None, ge=1, le=4),
    tipo: str | None = Query(None, regex="^(ACTIVO|PASIVO|PATRIMONIO|INGRESO|GASTO)$"),
    activo: bool | None = None,
    imputable: bool | None = None,
    buscar: str | None = Query(None, description="Buscar en código o nombre"),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    stmt = select(PlanCuentas).where(PlanCuentas.tenant_id == tenant_id)
    if nivel:
        stmt = stmt.where(PlanCuentas.nivel == nivel)
    if tipo:
        stmt = stmt.where(PlanCuentas.tipo == tipo)
    if activo is not None:
        stmt = stmt.where(PlanCuentas.activo == activo)
    if imputable is not None:
        stmt = stmt.where(PlanCuentas.imputable == imputable)
    if buscar:
        stmt = stmt.where(
            or_(PlanCuentas.codigo.ilike(f"%{buscar}%"), PlanCuentas.nombre.ilike(f"%{buscar}%"))
        )
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()
    stmt = stmt.order_by(PlanCuentas.codigo)
    result = db.execute(stmt)
    cuentas = result.scalars().all()
    return PlanCuentasList(items=[PlanCuentasResponse.from_orm(c) for c in cuentas], total=total)


@router.post(
    "/plan-cuentas", response_model=PlanCuentasResponse, status_code=status.HTTP_201_CREATED
)
async def create_cuenta(
    data: PlanCuentasCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    stmt = select(PlanCuentas).where(
        PlanCuentas.tenant_id == tenant_id, PlanCuentas.codigo == data.codigo
    )
    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una cuenta con código {data.codigo}",
        )
    if data.padre_id:
        stmt = select(PlanCuentas).where(
            PlanCuentas.id == data.padre_id, PlanCuentas.tenant_id == tenant_id
        )
        padre = db.execute(stmt).scalar_one_or_none()
        if not padre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta padre no encontrada"
            )
    cuenta = PlanCuentas(tenant_id=tenant_id, **data.dict())
    db.add(cuenta)
    db.commit()
    db.refresh(cuenta)
    return PlanCuentasResponse.from_orm(cuenta)


@router.get("/plan-cuentas/{cuenta_id}", response_model=PlanCuentasResponse)
async def get_cuenta(
    cuenta_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    stmt = select(PlanCuentas).where(
        PlanCuentas.id == cuenta_id, PlanCuentas.tenant_id == tenant_id
    )
    cuenta = db.execute(stmt).scalar_one_or_none()
    if not cuenta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")
    return PlanCuentasResponse.from_orm(cuenta)


@router.put("/plan-cuentas/{cuenta_id}", response_model=PlanCuentasResponse)
async def update_cuenta(
    cuenta_id: UUID,
    data: PlanCuentasUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    stmt = select(PlanCuentas).where(
        PlanCuentas.id == cuenta_id, PlanCuentas.tenant_id == tenant_id
    )
    cuenta = db.execute(stmt).scalar_one_or_none()
    if not cuenta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cuenta, key, value)
    db.commit()
    db.refresh(cuenta)
    return PlanCuentasResponse.from_orm(cuenta)


@router.delete("/plan-cuentas/{cuenta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cuenta(
    cuenta_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    stmt = select(PlanCuentas).where(
        PlanCuentas.id == cuenta_id, PlanCuentas.tenant_id == tenant_id
    )
    cuenta = db.execute(stmt).scalar_one_or_none()
    if not cuenta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")
    stmt = select(func.count()).select_from(AsientoLinea).where(AsientoLinea.cuenta_id == cuenta_id)
    count = db.execute(stmt).scalar_one()
    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar la cuenta porque tiene {count} movimientos",
        )
    db.delete(cuenta)
    db.commit()


# ============================================================================
# ASIENTOS CONTABLES
# ============================================================================


@router.get("/asientos", response_model=AsientoContableList)
async def list_asientos(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    status: str | None = Query(None, regex="^(BORRADOR|CONTABILIZADO)$"),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    stmt = select(AsientoContable).where(AsientoContable.tenant_id == tenant_id)

    if fecha_desde:
        stmt = stmt.where(AsientoContable.fecha >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(AsientoContable.fecha <= fecha_hasta)
    if status:
        stmt = stmt.where(AsientoContable.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()
    total_pages = ceil(total / page_size)

    stmt = stmt.order_by(AsientoContable.fecha.desc(), AsientoContable.numero.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = db.execute(stmt)
    asientos = result.scalars().all()

    # Load lineas for each asiento
    for asiento in asientos:
        asiento.lineas = (
            db.execute(select(AsientoLinea).where(AsientoLinea.asiento_id == asiento.id))
            .scalars()
            .all()
        )

    return AsientoContableList(
        items=[AsientoContableResponse.from_orm(a) for a in asientos],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/asientos", response_model=AsientoContableResponse, status_code=status.HTTP_201_CREATED
)
async def create_asiento(
    data: AsientoContableCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    user_id = claims.get("user_id")

    # Generate numero
    numero = _generate_numero_asiento(db, tenant_id, data.fecha.year)

    # Calculate totals
    debe_total = sum(linea.debe for linea in data.lineas)
    haber_total = sum(linea.haber for linea in data.lineas)

    asiento = AsientoContable(
        tenant_id=tenant_id,
        numero=numero,
        fecha=data.fecha,
        tipo=data.tipo,
        descripcion=data.descripcion,
        ref_doc_type=data.ref_doc_type,
        ref_doc_id=data.ref_doc_id,
        debe_total=debe_total,
        haber_total=haber_total,
        cuadrado=abs(debe_total - haber_total) < Decimal("0.01"),
        status="BORRADOR",
        created_by=user_id,
    )
    db.add(asiento)
    db.flush()  # Get ID

    # Create lineas
    for i, linea_data in enumerate(data.lineas):
        linea = AsientoLinea(
            asiento_id=asiento.id,
            cuenta_id=linea_data.cuenta_id,
            debe=linea_data.debe,
            haber=linea_data.haber,
            descripcion=linea_data.descripcion,
            orden=i + 1,
        )
        db.add(linea)

    db.commit()
    db.refresh(asiento)
    asiento.lineas = (
        db.execute(select(AsientoLinea).where(AsientoLinea.asiento_id == asiento.id))
        .scalars()
        .all()
    )

    return AsientoContableResponse.from_orm(asiento)


@router.get("/asientos/{asiento_id}", response_model=AsientoContableResponse)
async def get_asiento(
    asiento_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    stmt = select(AsientoContable).where(
        AsientoContable.id == asiento_id, AsientoContable.tenant_id == tenant_id
    )
    asiento = db.execute(stmt).scalar_one_or_none()
    if not asiento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asiento no encontrado")

    asiento.lineas = (
        db.execute(select(AsientoLinea).where(AsientoLinea.asiento_id == asiento.id))
        .scalars()
        .all()
    )

    return AsientoContableResponse.from_orm(asiento)


@router.put("/asientos/{asiento_id}", response_model=AsientoContableResponse)
async def update_asiento(
    asiento_id: UUID,
    data: AsientoContableUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    stmt = select(AsientoContable).where(
        AsientoContable.id == asiento_id, AsientoContable.tenant_id == tenant_id
    )
    asiento = db.execute(stmt).scalar_one_or_none()
    if not asiento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asiento no encontrado")

    if asiento.status == "CONTABILIZADO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede modificar un asiento contabilizado",
        )

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(asiento, key, value)

    db.commit()
    db.refresh(asiento)
    asiento.lineas = (
        db.execute(select(AsientoLinea).where(AsientoLinea.asiento_id == asiento.id))
        .scalars()
        .all()
    )

    return AsientoContableResponse.from_orm(asiento)


@router.post("/asientos/{asiento_id}/contabilizar", response_model=AsientoContableResponse)
async def contabilizar_asiento(
    asiento_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    user_id = claims.get("user_id")

    stmt = select(AsientoContable).where(
        AsientoContable.id == asiento_id, AsientoContable.tenant_id == tenant_id
    )
    asiento = db.execute(stmt).scalar_one_or_none()
    if not asiento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asiento no encontrado")

    if asiento.status == "CONTABILIZADO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Asiento ya contabilizado"
        )

    if not asiento.cuadrado:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asiento no cuadrado")

    asiento.status = "CONTABILIZADO"
    asiento.contabilizado_by = user_id
    asiento.contabilizado_at = datetime.now()

    # Update saldos de cuentas
    lineas = (
        db.execute(select(AsientoLinea).where(AsientoLinea.asiento_id == asiento.id))
        .scalars()
        .all()
    )

    for linea in lineas:
        _recalcular_saldos_cuenta(db, linea.cuenta_id)

    db.commit()
    db.refresh(asiento)
    asiento.lineas = lineas

    return AsientoContableResponse.from_orm(asiento)


# Alias for frontend compatibility
@router.get("/movimientos", response_model=AsientoContableList)
async def list_movimientos(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Alias para list_asientos - compatibilidad con frontend"""
    return await list_asientos(
        page=page,
        page_size=page_size,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        status="CONTABILIZADO",
        db=db,
        claims=claims,
    )
