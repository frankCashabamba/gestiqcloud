"""
Finanzas Module - HTTP API Tenant Interface

Funcionalidades completas:
- Gestión de movimientos de caja (ingresos/egresos)
- Apertura y cierre de caja diaria
- Conciliación y cuadre de caja
- Gestión de movimientos bancarios
- Conciliación bancaria
- Consulta de saldos (caja y banco)
- Estadísticas y reportes por período

Compatible con retail, hostelería y cualquier negocio con caja física.

MIGRADO DE:
- app/routers/finance.py (banco - parcial)
- app/routers/finance_complete.py (caja completa)
"""

from datetime import date, datetime
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
from app.models.core.facturacion import BankTransaction

# Models
from app.models.finance.cash_management import CashClosing as CierreCaja
from app.models.finance.cash_management import CashMovement as CajaMovimiento

# Schemas - Caja
from app.schemas.finance_caja import (
    CajaMovimientoCreate,
    CajaMovimientoList,
    CajaMovimientoResponse,
    CajaSaldoResponse,
    CajaStats,
    CierreCajaClose,
    CierreCajaCreate,
    CierreCajaList,
    CierreCajaResponse,
)

router = APIRouter(
    prefix="/finance",
    tags=["Finance"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# HELPERS - Funciones auxiliares
# ============================================================================


def _get_cierre_abierto(
    db: Session, tenant_id: UUID, fecha: date, caja_id: UUID | None = None
) -> CierreCaja | None:
    """Busca un cierre abierto para la fecha y caja especificadas"""
    stmt = select(CierreCaja).where(
        CierreCaja.tenant_id == tenant_id, CierreCaja.fecha == fecha, CierreCaja.status == "ABIERTO"
    )

    if caja_id:
        stmt = stmt.where(CierreCaja.caja_id == caja_id)
    else:
        stmt = stmt.where(CierreCaja.caja_id.is_(None))

    return db.execute(stmt).scalar_one_or_none()


def _calcular_totales_dia(
    db: Session, tenant_id: UUID, fecha: date, caja_id: UUID | None = None
) -> dict:
    """Calcula totales de ingresos y egresos del día"""
    stmt = select(
        func.sum(CajaMovimiento.importe).filter(CajaMovimiento.importe > 0).label("ingresos"),
        func.sum(CajaMovimiento.importe).filter(CajaMovimiento.importe < 0).label("egresos"),
    ).where(CajaMovimiento.tenant_id == tenant_id, CajaMovimiento.fecha == fecha)

    if caja_id:
        stmt = stmt.where(CajaMovimiento.caja_id == caja_id)
    else:
        stmt = stmt.where(CajaMovimiento.caja_id.is_(None))

    result = db.execute(stmt).one()

    ingresos = result.ingresos or Decimal("0")
    egresos = abs(result.egresos or Decimal("0"))

    return {"total_ingresos": ingresos, "total_egresos": egresos}


# ============================================================================
# ENDPOINTS - MOVIMIENTOS DE CAJA
# ============================================================================


@router.get(
    "/caja/movimientos", response_model=CajaMovimientoList, summary="Listar movimientos de caja"
)
async def list_movimientos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    tipo: str | None = Query(None, regex="^(INGRESO|EGRESO|AJUSTE)$"),
    categoria: str | None = None,
    caja_id: UUID | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """
    Lista movimientos de caja con filtros.

    **Filtros:**
    - fecha_desde/fecha_hasta: Rango de fechas
    - tipo: INGRESO, EGRESO, AJUSTE
    - categoria: VENTA, COMPRA, GASTO, etc.
    - caja_id: Filtrar por caja específica
    """
    tenant_id = claims["tenant_id"]

    stmt = select(CajaMovimiento).where(CajaMovimiento.tenant_id == tenant_id)

    if fecha_desde:
        stmt = stmt.where(CajaMovimiento.fecha >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(CajaMovimiento.fecha <= fecha_hasta)
    if tipo:
        stmt = stmt.where(CajaMovimiento.tipo == tipo)
    if categoria:
        stmt = stmt.where(CajaMovimiento.categoria == categoria)
    if caja_id:
        stmt = stmt.where(CajaMovimiento.caja_id == caja_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    stmt = (
        stmt.order_by(CajaMovimiento.fecha.desc(), CajaMovimiento.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = db.execute(stmt)
    movimientos = result.scalars().all()

    return CajaMovimientoList(
        items=[CajaMovimientoResponse.from_orm(m) for m in movimientos],
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=ceil(total / limit) if total > 0 else 0,
    )


@router.post(
    "/caja/movimientos",
    response_model=CajaMovimientoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear movimiento de caja",
)
async def create_movimiento(
    data: CajaMovimientoCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """
    Crea un nuevo movimiento de caja.

    Si existe un cierre abierto para la fecha, se vincula automáticamente.
    """
    tenant_id = claims["tenant_id"]
    user_id = claims["user_id"]

    cierre = _get_cierre_abierto(db, tenant_id, data.fecha, data.caja_id)

    movimiento = CajaMovimiento(
        tenant_id=tenant_id,
        usuario_id=user_id,
        cierre_id=cierre.id if cierre else None,
        **data.dict(),
    )

    db.add(movimiento)

    if cierre:
        totales = _calcular_totales_dia(db, tenant_id, data.fecha, data.caja_id)
        cierre.total_ingresos = totales["total_ingresos"]
        cierre.total_egresos = totales["total_egresos"]
        cierre.saldo_teorico = cierre.saldo_inicial + cierre.total_ingresos - cierre.total_egresos

    db.commit()
    db.refresh(movimiento)

    return CajaMovimientoResponse.from_orm(movimiento)


@router.get("/caja/saldo", response_model=CajaSaldoResponse, summary="Obtener saldo actual de caja")
async def get_saldo_actual(
    fecha: date | None = Query(None, description="Fecha (por defecto hoy)"),
    caja_id: UUID | None = None,
    moneda: str = Query("EUR", description="Moneda"),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """
    Obtiene el saldo actual de caja.

    Calcula:
    - Saldo inicial (del cierre o del día anterior)
    - Total ingresos del día
    - Total egresos del día
    - Saldo actual (inicial + ingresos - egresos)
    """
    tenant_id = claims["tenant_id"]
    fecha_consulta = fecha or date.today()

    cierre_hoy = _get_cierre_abierto(db, tenant_id, fecha_consulta, caja_id)

    if cierre_hoy:
        return CajaSaldoResponse(
            fecha=fecha_consulta,
            moneda=moneda,
            saldo_inicial=cierre_hoy.saldo_inicial,
            total_ingresos_hoy=cierre_hoy.total_ingresos,
            total_egresos_hoy=cierre_hoy.total_egresos,
            saldo_actual=cierre_hoy.saldo_teorico,
            caja_id=caja_id,
            tiene_cierre_abierto=True,
        )
    else:
        stmt = select(CierreCaja).where(
            CierreCaja.tenant_id == tenant_id,
            CierreCaja.fecha < fecha_consulta,
            CierreCaja.status == "CERRADO",
        )

        if caja_id:
            stmt = stmt.where(CierreCaja.caja_id == caja_id)
        else:
            stmt = stmt.where(CierreCaja.caja_id.is_(None))

        stmt = stmt.order_by(CierreCaja.fecha.desc()).limit(1)
        ultimo_cierre = db.execute(stmt).scalar_one_or_none()

        saldo_inicial = ultimo_cierre.saldo_real if ultimo_cierre else Decimal("0")
        totales = _calcular_totales_dia(db, tenant_id, fecha_consulta, caja_id)

        return CajaSaldoResponse(
            fecha=fecha_consulta,
            moneda=moneda,
            saldo_inicial=saldo_inicial,
            total_ingresos_hoy=totales["total_ingresos"],
            total_egresos_hoy=totales["total_egresos"],
            saldo_actual=saldo_inicial + totales["total_ingresos"] - totales["total_egresos"],
            caja_id=caja_id,
            tiene_cierre_abierto=False,
        )


# ============================================================================
# ENDPOINTS - CIERRES DE CAJA
# ============================================================================


@router.get(
    "/caja/cierre-diario", response_model=CierreCajaResponse, summary="Obtener cierre diario"
)
async def get_cierre_diario(
    fecha: date | None = Query(None, description="Fecha (por defecto hoy)"),
    caja_id: UUID | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Obtiene el cierre de caja del día (o crea uno si no existe)"""
    tenant_id = claims["tenant_id"]
    fecha_consulta = fecha or date.today()

    cierre = _get_cierre_abierto(db, tenant_id, fecha_consulta, caja_id)

    if not cierre:
        stmt = select(CierreCaja).where(
            CierreCaja.tenant_id == tenant_id, CierreCaja.fecha == fecha_consulta
        )

        if caja_id:
            stmt = stmt.where(CierreCaja.caja_id == caja_id)
        else:
            stmt = stmt.where(CierreCaja.caja_id.is_(None))

        cierre = db.execute(stmt).scalar_one_or_none()

    if not cierre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe cierre para la fecha {fecha_consulta}. Use POST /caja/cierre para crear uno.",
        )

    return CierreCajaResponse.from_orm(cierre)


@router.post(
    "/caja/cierre",
    response_model=CierreCajaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Abrir caja",
)
async def abrir_caja(
    data: CierreCajaCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Abre caja para el día (crea cierre en estado ABIERTO)"""
    tenant_id = claims["tenant_id"]
    user_id = claims["user_id"]

    cierre_existe = _get_cierre_abierto(db, tenant_id, data.fecha, data.caja_id)
    if cierre_existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un cierre abierto para la fecha {data.fecha}",
        )

    stmt = select(CierreCaja).where(
        CierreCaja.tenant_id == tenant_id,
        CierreCaja.fecha < data.fecha,
        CierreCaja.status == "CERRADO",
    )

    if data.caja_id:
        stmt = stmt.where(CierreCaja.caja_id == data.caja_id)
    else:
        stmt = stmt.where(CierreCaja.caja_id.is_(None))

    stmt = stmt.order_by(CierreCaja.fecha.desc()).limit(1)
    ultimo_cierre = db.execute(stmt).scalar_one_or_none()

    saldo_inicial = data.saldo_inicial
    if saldo_inicial == Decimal("0") and ultimo_cierre:
        saldo_inicial = ultimo_cierre.saldo_real

    cierre = CierreCaja(
        tenant_id=tenant_id,
        fecha=data.fecha,
        caja_id=data.caja_id,
        moneda=data.moneda,
        saldo_inicial=saldo_inicial,
        saldo_teorico=saldo_inicial,
        status="ABIERTO",
        abierto_por=user_id,
        abierto_at=datetime.utcnow(),
        notas=data.notas,
    )

    db.add(cierre)
    db.commit()
    db.refresh(cierre)

    return CierreCajaResponse.from_orm(cierre)


@router.post(
    "/caja/cierre/{cierre_id}/cerrar", response_model=CierreCajaResponse, summary="Cerrar caja"
)
async def cerrar_caja(
    cierre_id: UUID,
    data: CierreCajaClose,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Cierra caja (marca cierre como CERRADO)"""
    tenant_id = claims["tenant_id"]
    user_id = claims["user_id"]

    stmt = select(CierreCaja).where(CierreCaja.id == cierre_id, CierreCaja.tenant_id == tenant_id)
    cierre = db.execute(stmt).scalar_one_or_none()

    if not cierre:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cierre no encontrado")

    if cierre.status != "ABIERTO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El cierre ya está en estado {cierre.status}",
        )

    totales = _calcular_totales_dia(db, tenant_id, cierre.fecha, cierre.caja_id)
    cierre.total_ingresos = totales["total_ingresos"]
    cierre.total_egresos = totales["total_egresos"]
    cierre.saldo_teorico = cierre.saldo_inicial + cierre.total_ingresos - cierre.total_egresos

    cierre.saldo_real = data.saldo_real
    cierre.diferencia = cierre.saldo_real - cierre.saldo_teorico
    cierre.cuadrado = cierre.diferencia == Decimal("0")

    if data.detalles_billetes:
        total_contado = data.detalles_billetes.calcular_total()
        if abs(total_contado - data.saldo_real) > Decimal("0.01"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El desglose de billetes ({total_contado}) no coincide con saldo real ({data.saldo_real})",
            )
        cierre.detalles_billetes = data.detalles_billetes.dict()

    if data.notas:
        cierre.notas = (cierre.notas or "") + f"\n[CIERRE] {data.notas}"

    cierre.status = "CERRADO" if cierre.cuadrado else "PENDIENTE"
    cierre.cerrado_por = user_id
    cierre.cerrado_at = datetime.utcnow()

    db.commit()
    db.refresh(cierre)

    return CierreCajaResponse.from_orm(cierre)


@router.get("/caja/cierres", response_model=CierreCajaList, summary="Listar cierres de caja")
async def list_cierres(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    status: str | None = Query(None, regex="^(ABIERTO|CERRADO|PENDIENTE)$"),
    caja_id: UUID | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Lista cierres de caja con filtros"""
    tenant_id = claims["tenant_id"]

    stmt = select(CierreCaja).where(CierreCaja.tenant_id == tenant_id)

    if fecha_desde:
        stmt = stmt.where(CierreCaja.fecha >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(CierreCaja.fecha <= fecha_hasta)
    if status:
        stmt = stmt.where(CierreCaja.status == status)
    if caja_id:
        stmt = stmt.where(CierreCaja.caja_id == caja_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(CierreCaja.fecha.desc()).offset(skip).limit(limit)

    result = db.execute(stmt)
    cierres = result.scalars().all()

    return CierreCajaList(
        items=[CierreCajaResponse.from_orm(c) for c in cierres],
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=ceil(total / limit) if total > 0 else 0,
    )


@router.get("/caja/stats", response_model=CajaStats, summary="Estadísticas de caja")
async def get_caja_stats(
    fecha_desde: date = Query(..., description="Fecha inicio"),
    fecha_hasta: date = Query(..., description="Fecha fin"),
    caja_id: UUID | None = None,
    moneda: str = Query("EUR", description="Moneda"),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Estadísticas de caja por período"""
    tenant_id = claims["tenant_id"]

    stmt = select(CajaMovimiento).where(
        CajaMovimiento.tenant_id == tenant_id,
        CajaMovimiento.fecha >= fecha_desde,
        CajaMovimiento.fecha <= fecha_hasta,
        CajaMovimiento.moneda == moneda,
    )

    if caja_id:
        stmt = stmt.where(CajaMovimiento.caja_id == caja_id)

    result = db.execute(
        select(
            func.sum(CajaMovimiento.importe).filter(CajaMovimiento.importe > 0),
            func.sum(CajaMovimiento.importe).filter(CajaMovimiento.importe < 0),
            func.count(),
        ).select_from(stmt.subquery())
    ).one()

    total_ingresos = result[0] or Decimal("0")
    total_egresos = abs(result[1] or Decimal("0"))
    total_movimientos = result[2] or 0

    ingresos_cat = {}
    egresos_cat = {}

    for cat in ["VENTA", "COMPRA", "GASTO", "NOMINA", "BANCO", "CAMBIO", "AJUSTE", "OTRO"]:
        result_ing = db.execute(
            select(func.sum(CajaMovimiento.importe)).select_from(
                stmt.where(
                    CajaMovimiento.tipo == "INGRESO", CajaMovimiento.categoria == cat
                ).subquery()
            )
        ).scalar_one()
        ingresos_cat[cat] = result_ing or Decimal("0")

        result_egr = db.execute(
            select(func.sum(CajaMovimiento.importe)).select_from(
                stmt.where(
                    CajaMovimiento.tipo == "EGRESO", CajaMovimiento.categoria == cat
                ).subquery()
            )
        ).scalar_one()
        egresos_cat[cat] = abs(result_egr or Decimal("0"))

    dias = (fecha_hasta - fecha_desde).days + 1
    promedio_ingresos = total_ingresos / dias if dias > 0 else Decimal("0")
    promedio_egresos = total_egresos / dias if dias > 0 else Decimal("0")

    stmt_cierres = select(CierreCaja).where(
        CierreCaja.tenant_id == tenant_id,
        CierreCaja.fecha >= fecha_desde,
        CierreCaja.fecha <= fecha_hasta,
    )

    if caja_id:
        stmt_cierres = stmt_cierres.where(CierreCaja.caja_id == caja_id)

    total_cierres = db.execute(
        select(func.count()).select_from(stmt_cierres.subquery())
    ).scalar_one()

    cierres_cuadrados = db.execute(
        select(func.count()).select_from(stmt_cierres.where(CierreCaja.cuadrado).subquery())
    ).scalar_one()

    total_diferencias = db.execute(
        select(func.sum(CierreCaja.diferencia)).select_from(stmt_cierres.subquery())
    ).scalar_one() or Decimal("0")

    count_ingresos = db.execute(
        select(func.count()).select_from(stmt.where(CajaMovimiento.tipo == "INGRESO").subquery())
    ).scalar_one()

    count_egresos = db.execute(
        select(func.count()).select_from(stmt.where(CajaMovimiento.tipo == "EGRESO").subquery())
    ).scalar_one()

    return CajaStats(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        moneda=moneda,
        total_ingresos=total_ingresos,
        total_egresos=total_egresos,
        saldo_neto=total_ingresos - total_egresos,
        ingresos_por_categoria=ingresos_cat,
        egresos_por_categoria=egresos_cat,
        promedio_ingresos_dia=promedio_ingresos.quantize(Decimal("0.01")),
        promedio_egresos_dia=promedio_egresos.quantize(Decimal("0.01")),
        total_cierres=total_cierres,
        cierres_cuadrados=cierres_cuadrados,
        total_diferencias=total_diferencias,
        total_movimientos=total_movimientos,
        total_ingresos_count=count_ingresos,
        total_egresos_count=count_egresos,
    )


# ============================================================================
# ENDPOINTS - BANCO
# ============================================================================


@router.get("/banco/movimientos", response_model=dict, summary="List bank transactions")
def list_bank_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    date_from: str | None = None,
    date_to: str | None = None,
    tx_type: str | None = None,
    reconciled: bool | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """List bank transactions for the tenant."""
    tenant_id = UUID(claims["tenant_id"])

    query = db.query(BankTransaction).filter(BankTransaction.tenant_id == tenant_id)

    if date_from:
        query = query.filter(BankTransaction.date >= date_from)
    if date_to:
        query = query.filter(BankTransaction.date <= date_to)
    if tx_type:
        query = query.filter(BankTransaction.type == tx_type)
    if reconciled is not None:
        from app.models.core.facturacion import TransactionStatus

        status = TransactionStatus.RECONCILED if reconciled else TransactionStatus.PENDING
        query = query.filter(BankTransaction.status == status)

    total = query.count()
    transactions = query.order_by(BankTransaction.date.desc()).offset(skip).limit(limit).all()

    return {
        "items": [
            {
                "id": str(m.id),
                "tenant_id": str(m.tenant_id),
                "account_id": str(m.account_id),
                "date": m.date.isoformat() if m.date else None,
                "type": m.type.value if hasattr(m.type, "value") else m.type,
                "amount": float(m.amount),
                "concept": m.concept,
                "status": m.status.value if hasattr(m.status, "value") else m.status,
            }
            for m in transactions
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("/banco/{id}/conciliar", response_model=dict, summary="Reconcile bank transaction")
def reconcile_transaction(
    id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Mark bank transaction as reconciled."""
    tenant_id = UUID(claims["tenant_id"])

    tx = (
        db.query(BankTransaction)
        .filter(and_(BankTransaction.id == id, BankTransaction.tenant_id == tenant_id))
        .first()
    )

    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    from app.models.core.facturacion import TransactionStatus

    if tx.status == TransactionStatus.RECONCILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This transaction is already reconciled",
        )

    tx.status = TransactionStatus.RECONCILED
    db.commit()
    db.refresh(tx)

    return {
        "id": str(tx.id),
        "status": tx.status.value,
        "message": "Transaction reconciled",
    }


@router.get("/banco/saldos", response_model=list, summary="Get bank balances")
def get_bank_balances(
    date_filter: str | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Get bank balances per account."""
    tenant_id = UUID(claims["tenant_id"])

    query = db.query(BankTransaction).filter(BankTransaction.tenant_id == tenant_id)

    if date_filter:
        query = query.filter(BankTransaction.date <= date_filter)

    accounts_data = (
        query.with_entities(
            BankTransaction.account_id, func.sum(BankTransaction.amount).label("balance")
        )
        .group_by(BankTransaction.account_id)
        .all()
    )

    return [
        {
            "account_id": str(acc.account_id),
            "balance": float(acc.balance or 0),
            "date": date_filter or datetime.utcnow().date().isoformat(),
        }
        for acc in accounts_data
    ]
