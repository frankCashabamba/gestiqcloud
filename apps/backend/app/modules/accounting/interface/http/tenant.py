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

import logging
from datetime import date, datetime
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.accounting.chart_of_accounts import ChartOfAccounts as PlanCuentas
from app.models.accounting.chart_of_accounts import JournalEntry as AsientoContable
from app.models.accounting.chart_of_accounts import JournalEntryLine as AsientoLinea
from app.models.accounting.pos_settings import PaymentMethod, TenantAccountingSettings
from app.schemas.accounting import (
    AsientoContableCreate,
    AsientoContableList,
    AsientoContableResponse,
    AsientoContableUpdate,
    AsientoLineaResponse,
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

logger = logging.getLogger(__name__)


# HELPERS
def _generate_numero_asiento(db: Session, tenant_id: UUID, ano: int) -> str:
    """Genera número único de asiento: ASI-YYYY-NNNN"""
    prefix = f"ASI-{ano}-"
    stmt = (
        select(AsientoContable)
        .where(AsientoContable.tenant_id == tenant_id, AsientoContable.number.like(f"{prefix}%"))
        .order_by(AsientoContable.number.desc())
        .limit(1)
    )
    result = db.execute(stmt)
    last_asiento = result.scalar_one_or_none()
    if last_asiento and last_asiento.number:
        try:
            last_num = int(last_asiento.number.split("-")[-1])
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
        select(func.sum(AsientoLinea.debit), func.sum(AsientoLinea.credit))
        .join(AsientoContable)
        .where(AsientoLinea.account_id == cuenta_id, AsientoContable.status == "POSTED")
    )
    result = db.execute(stmt).one()
    debe = result[0] or Decimal("0")
    haber = result[1] or Decimal("0")
    cuenta.saldo_debe = debe
    cuenta.saldo_haber = haber
    cuenta.saldo = debe - haber


# =========================
# Pydantic auxiliares POS
# =========================


class AccountingSettingsPayload(BaseModel):
    cash_account_id: UUID
    bank_account_id: UUID
    sales_bakery_account_id: UUID | None = None
    vat_output_account_id: UUID
    loss_account_id: UUID | None = None
    ap_account_id: UUID | None = None
    vat_input_account_id: UUID | None = None
    default_expense_account_id: UUID | None = None


class PaymentMethodPayload(BaseModel):
    name: str
    description: str | None = None
    account_id: UUID
    is_active: bool = True


def _serialize_cuenta(c: PlanCuentas) -> dict:
    type_map_rev = {
        "ASSET": "ACTIVO",
        "LIABILITY": "PASIVO",
        "EQUITY": "PATRIMONIO",
        "INCOME": "INGRESO",
        "EXPENSE": "GASTO",
    }
    return {
        "id": str(c.id),
        "tenant_id": str(c.tenant_id),
        "codigo": c.code,
        "nombre": c.name,
        "descripcion": c.description,
        "tipo": type_map_rev.get(c.type, c.type),
        "nivel": c.level,
        "padre_id": str(c.parent_id) if c.parent_id else None,
        "imputable": c.can_post,
        "activo": c.active,
        "saldo_debe": float(c.debit_balance or 0),
        "saldo_haber": float(c.credit_balance or 0),
        "saldo": float((c.debit_balance or 0) - (c.credit_balance or 0)),
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


def _asiento_to_response(asiento: AsientoContable) -> AsientoContableResponse:
    """Mapea JournalEntry -> schema AsientoContableResponse (nombres en español)."""
    type_map_rev = {
        "OPENING": "APERTURA",
        "OPERATIONS": "OPERACIONES",
        "REGULARIZATION": "REGULARIZACION",
        "CLOSING": "CIERRE",
    }
    lineas: list[AsientoLineaResponse] = []
    for linea in asiento.lines:
        lineas.append(
            AsientoLineaResponse(
                id=linea.id,
                asiento_id=asiento.id,
                cuenta_id=linea.account_id,
                debe=linea.debit,
                haber=linea.credit,
                descripcion=linea.description,
                orden=linea.line_number,
                created_at=linea.created_at,
                cuenta_codigo=getattr(linea.account, "code", None),
                cuenta_nombre=getattr(linea.account, "name", None),
            )
        )

    payload = {
        "id": asiento.id,
        "tenant_id": asiento.tenant_id,
        "numero": asiento.number,
        "fecha": asiento.date,
        "tipo": type_map_rev.get(asiento.type, asiento.type),
        "descripcion": asiento.description,
        "ref_doc_type": asiento.ref_doc_type,
        "ref_doc_id": asiento.ref_doc_id,
        "debe_total": asiento.debit_total,
        "haber_total": asiento.credit_total,
        "cuadrado": asiento.is_balanced,
        "status": asiento.status,
        "created_by": asiento.created_by,
        "contabilizado_by": asiento.posted_by,
        "contabilizado_at": asiento.posted_at,
        "created_at": asiento.created_at,
        "updated_at": asiento.updated_at,
        "lineas": lineas,
    }
    return AsientoContableResponse.model_validate(payload)


def _map_tipo_to_account_type(tipo: str) -> str:
    type_map = {
        "ACTIVO": "ASSET",
        "PASIVO": "LIABILITY",
        "PATRIMONIO": "EQUITY",
        "INGRESO": "INCOME",
        "GASTO": "EXPENSE",
    }
    if not tipo:
        return tipo
    return type_map.get(tipo.upper(), tipo.upper())


@router.get("/chart-of-accounts", response_model=PlanCuentasList)
async def list_cuentas(
    nivel: int | None = Query(None, ge=1, le=4),
    tipo: str | None = Query(None, pattern="^(ACTIVO|PASIVO|PATRIMONIO|INGRESO|GASTO)$"),
    activo: bool | None = None,
    imputable: bool | None = None,
    buscar: str | None = Query(None, description="Buscar en código o nombre"),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    stmt = select(PlanCuentas).where(PlanCuentas.tenant_id == tenant_id)
    if nivel:
        stmt = stmt.where(PlanCuentas.level == nivel)
    if tipo:
        stmt = stmt.where(PlanCuentas.type == tipo)
    if activo is not None:
        stmt = stmt.where(PlanCuentas.active == activo)
    if imputable is not None:
        # en este modelo, can_post indica si es imputable
        stmt = stmt.where(PlanCuentas.can_post == imputable)
    if buscar:
        stmt = stmt.where(
            or_(PlanCuentas.code.ilike(f"%{buscar}%"), PlanCuentas.name.ilike(f"%{buscar}%"))
        )
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()
    stmt = stmt.order_by(PlanCuentas.code)
    result = db.execute(stmt)
    cuentas = result.scalars().all()
    return PlanCuentasList(items=[_serialize_cuenta(c) for c in cuentas], total=total)


@router.post(
    "/chart-of-accounts", response_model=PlanCuentasResponse, status_code=status.HTTP_201_CREATED
)
async def create_cuenta(
    data: PlanCuentasCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    stmt = select(PlanCuentas).where(
        PlanCuentas.tenant_id == tenant_id, PlanCuentas.code == data.codigo
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
    payload = data.dict()
    payload["code"] = payload.pop("codigo")
    payload["name"] = payload.pop("nombre")
    if "descripcion" in payload:
        payload["description"] = payload.pop("descripcion")
    # Mapear tipo español -> enum inglés
    payload["type"] = _map_tipo_to_account_type(payload.pop("tipo"))
    payload["level"] = payload.pop("nivel")
    payload["can_post"] = payload.pop("imputable")
    payload["active"] = payload.pop("activo")
    payload["parent_id"] = payload.pop("padre_id")

    # Seguridad extra: asegurar type en inglés
    payload["type"] = _map_tipo_to_account_type(payload.get("type", ""))

    cuenta = PlanCuentas(tenant_id=tenant_id, **payload)
    db.add(cuenta)
    db.commit()
    db.refresh(cuenta)
    return _serialize_cuenta(cuenta)


@router.get("/chart-of-accounts/{cuenta_id}", response_model=PlanCuentasResponse)
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
    return _serialize_cuenta(cuenta)


@router.put("/chart-of-accounts/{cuenta_id}", response_model=PlanCuentasResponse)
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
    if "codigo" in update_data:
        cuenta.code = update_data["codigo"]
    if "nombre" in update_data:
        cuenta.name = update_data["nombre"]
    if "descripcion" in update_data:
        cuenta.description = update_data["descripcion"]
    if "tipo" in update_data:
        cuenta.type = _map_tipo_to_account_type(update_data["tipo"])
    if "nivel" in update_data:
        cuenta.level = update_data["nivel"]
    if "padre_id" in update_data:
        cuenta.parent_id = update_data["padre_id"]
    if "imputable" in update_data:
        cuenta.can_post = update_data["imputable"]
    if "activo" in update_data:
        cuenta.active = update_data["activo"]
    db.commit()
    db.refresh(cuenta)
    return _serialize_cuenta(cuenta)


@router.delete("/chart-of-accounts/{cuenta_id}", status_code=status.HTTP_204_NO_CONTENT)
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


# ===========================================
# Configuración contable POS (settings + pagos)
# ===========================================


@router.get("/pos/settings", response_model=dict)
async def get_pos_accounting_settings(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tid = claims["tenant_id"]
    cfg = db.query(TenantAccountingSettings).filter_by(tenant_id=tid).first()
    if not cfg:
        # Return empty defaults instead of 404 so the UI can bootstrap config gracefully.
        return {
            "cash_account_id": None,
            "bank_account_id": None,
            "sales_bakery_account_id": None,
            "vat_output_account_id": None,
            "loss_account_id": None,
            "ap_account_id": None,
            "vat_input_account_id": None,
            "default_expense_account_id": None,
        }
    logger.info(
        "POS accounting settings loaded for tenant_id=%s cash_account_id=%s bank_account_id=%s sales_account_id=%s vat_output_account_id=%s loss_account_id=%s",
        tid,
        cfg.cash_account_id,
        cfg.bank_account_id,
        cfg.sales_bakery_account_id,
        cfg.vat_output_account_id,
        cfg.loss_account_id,
    )
    return {
        "cash_account_id": str(cfg.cash_account_id),
        "bank_account_id": str(cfg.bank_account_id),
        "sales_bakery_account_id": (
            str(cfg.sales_bakery_account_id) if cfg.sales_bakery_account_id else None
        ),
        "vat_output_account_id": str(cfg.vat_output_account_id),
        "loss_account_id": str(cfg.loss_account_id) if cfg.loss_account_id else None,
        "ap_account_id": str(cfg.ap_account_id) if getattr(cfg, "ap_account_id", None) else None,
        "vat_input_account_id": (
            str(cfg.vat_input_account_id) if getattr(cfg, "vat_input_account_id", None) else None
        ),
        "default_expense_account_id": (
            str(cfg.default_expense_account_id)
            if getattr(cfg, "default_expense_account_id", None)
            else None
        ),
    }


@router.put("/pos/settings", response_model=dict, status_code=200)
async def upsert_pos_accounting_settings(
    payload: AccountingSettingsPayload,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tid = claims["tenant_id"]
    cfg = db.query(TenantAccountingSettings).filter_by(tenant_id=tid).first()
    if not cfg:
        cfg = TenantAccountingSettings(tenant_id=tid)
        db.add(cfg)

    cfg.cash_account_id = payload.cash_account_id
    cfg.bank_account_id = payload.bank_account_id
    cfg.sales_bakery_account_id = payload.sales_bakery_account_id
    cfg.vat_output_account_id = payload.vat_output_account_id
    cfg.loss_account_id = payload.loss_account_id
    cfg.ap_account_id = payload.ap_account_id
    cfg.vat_input_account_id = payload.vat_input_account_id
    cfg.default_expense_account_id = payload.default_expense_account_id

    db.commit()
    db.refresh(cfg)
    logger.info(
        "POS accounting settings saved for tenant_id=%s cash_account_id=%s bank_account_id=%s sales_account_id=%s vat_output_account_id=%s loss_account_id=%s",
        tid,
        cfg.cash_account_id,
        cfg.bank_account_id,
        cfg.sales_bakery_account_id,
        cfg.vat_output_account_id,
        cfg.loss_account_id,
    )
    return {
        "cash_account_id": str(cfg.cash_account_id),
        "bank_account_id": str(cfg.bank_account_id),
        "sales_bakery_account_id": str(cfg.sales_bakery_account_id),
        "vat_output_account_id": str(cfg.vat_output_account_id),
        "loss_account_id": str(cfg.loss_account_id) if cfg.loss_account_id else None,
        "ap_account_id": str(cfg.ap_account_id) if cfg.ap_account_id else None,
        "vat_input_account_id": str(cfg.vat_input_account_id) if cfg.vat_input_account_id else None,
        "default_expense_account_id": (
            str(cfg.default_expense_account_id) if cfg.default_expense_account_id else None
        ),
    }


@router.get("/pos/payment-methods", response_model=list[dict])
async def list_payment_methods(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tid = claims["tenant_id"]
    methods = (
        db.query(PaymentMethod).filter_by(tenant_id=tid).order_by(PaymentMethod.name.asc()).all()
    )
    return [
        {
            "id": str(m.id),
            "name": m.name,
            "description": m.description,
            "account_id": str(m.account_id),
            "is_active": m.is_active,
        }
        for m in methods
    ]


@router.post("/pos/payment-methods", response_model=dict, status_code=201)
async def create_payment_method(
    payload: PaymentMethodPayload,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tid = claims["tenant_id"]
    existing = db.query(PaymentMethod).filter_by(tenant_id=tid, name=payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un medio de pago con ese nombre")

    pm = PaymentMethod(
        tenant_id=tid,
        name=payload.name,
        description=payload.description,
        account_id=payload.account_id,
        is_active=payload.is_active,
    )
    db.add(pm)
    db.commit()
    db.refresh(pm)
    return {
        "id": str(pm.id),
        "name": pm.name,
        "description": pm.description,
        "account_id": str(pm.account_id),
        "is_active": pm.is_active,
    }


@router.put("/pos/payment-methods/{method_id}", response_model=dict)
async def update_payment_method(
    method_id: UUID,
    payload: PaymentMethodPayload,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tid = claims["tenant_id"]
    pm = db.query(PaymentMethod).filter_by(id=method_id, tenant_id=tid).first()
    if not pm:
        raise HTTPException(status_code=404, detail="Medio de pago no encontrado")

    # Validar duplicado de nombre
    dup = (
        db.query(PaymentMethod)
        .filter(
            PaymentMethod.tenant_id == tid,
            PaymentMethod.name == payload.name,
            PaymentMethod.id != method_id,
        )
        .first()
    )
    if dup:
        raise HTTPException(status_code=400, detail="Ya existe otro medio de pago con ese nombre")

    pm.name = payload.name
    pm.description = payload.description
    pm.account_id = payload.account_id
    pm.is_active = payload.is_active
    db.commit()
    db.refresh(pm)
    return {
        "id": str(pm.id),
        "name": pm.name,
        "description": pm.description,
        "account_id": str(pm.account_id),
        "is_active": pm.is_active,
    }


@router.delete("/pos/payment-methods/{method_id}", status_code=204)
async def delete_payment_method(
    method_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tid = claims["tenant_id"]
    pm = db.query(PaymentMethod).filter_by(id=method_id, tenant_id=tid).first()
    if not pm:
        raise HTTPException(status_code=404, detail="Medio de pago no encontrado")
    db.delete(pm)
    db.commit()


# ============================================================================
# ASIENTOS CONTABLES
# ============================================================================


@router.get("/journal-entries", response_model=AsientoContableList)
async def list_asientos(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    status: str | None = Query(None, pattern="^(DRAFT|POSTED)$"),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    stmt = select(AsientoContable).where(AsientoContable.tenant_id == tenant_id)

    if fecha_desde:
        stmt = stmt.where(AsientoContable.date >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(AsientoContable.date <= fecha_hasta)
    if status:
        stmt = stmt.where(AsientoContable.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()
    total_pages = ceil(total / page_size)

    stmt = stmt.order_by(AsientoContable.date.desc(), AsientoContable.number.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = db.execute(stmt)
    asientos = result.scalars().all()

    # Load lineas for each asiento
    for asiento in asientos:
        asiento.lineas = (
            db.execute(select(AsientoLinea).where(AsientoLinea.entry_id == asiento.id))
            .scalars()
            .all()
        )

    return AsientoContableList(
        items=[_asiento_to_response(a) for a in asientos],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/journal-entries", response_model=AsientoContableResponse, status_code=status.HTTP_201_CREATED
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
    debe_total = sum(linea.debit for linea in data.lineas)
    haber_total = sum(linea.credit for linea in data.lineas)

    asiento = AsientoContable(
        tenant_id=tenant_id,
        number=numero,
        date=data.fecha,
        type=data.tipo,
        description=data.descripcion,
        ref_doc_type=data.ref_doc_type,
        ref_doc_id=data.ref_doc_id,
        debit_total=debe_total,
        credit_total=haber_total,
        is_balanced=abs(debe_total - haber_total) < Decimal("0.01"),
        status="DRAFT",
        created_by=user_id,
    )
    db.add(asiento)
    db.flush()  # Get ID

    # Create lineas
    for i, linea_data in enumerate(data.lineas):
        linea = AsientoLinea(
            entry_id=asiento.id,
            account_id=linea_data.cuenta_id,
            debit=linea_data.debit,
            credit=linea_data.credit,
            description=linea_data.descripcion,
            line_number=i + 1,
        )
        db.add(linea)

    db.commit()
    db.refresh(asiento)
    asiento.lineas = (
        db.execute(select(AsientoLinea).where(AsientoLinea.entry_id == asiento.id)).scalars().all()
    )

    return _asiento_to_response(asiento)


@router.get("/journal-entries/{asiento_id}", response_model=AsientoContableResponse)
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
        db.execute(select(AsientoLinea).where(AsientoLinea.entry_id == asiento.id)).scalars().all()
    )

    return _asiento_to_response(asiento)


@router.put("/journal-entries/{asiento_id}", response_model=AsientoContableResponse)
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

    if asiento.status == "POSTED":
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
        db.execute(select(AsientoLinea).where(AsientoLinea.entry_id == asiento.id)).scalars().all()
    )

    return _asiento_to_response(asiento)


@router.post("/journal-entries/{asiento_id}/post", response_model=AsientoContableResponse)
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

    if asiento.status == "POSTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Asiento ya contabilizado"
        )

    if not asiento.is_balanced:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asiento no cuadrado")

    asiento.status = "POSTED"
    asiento.posted_by = user_id
    asiento.posted_at = datetime.now()

    # Update saldos de cuentas
    lineas = (
        db.execute(select(AsientoLinea).where(AsientoLinea.entry_id == asiento.id)).scalars().all()
    )

    for linea in lineas:
        _recalcular_saldos_cuenta(db, linea.cuenta_id)

    db.commit()
    db.refresh(asiento)
    asiento.lineas = lineas

    return _asiento_to_response(asiento)


# Alias for frontend compatibility
@router.get("/transactions", response_model=AsientoContableList)
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
        status="POSTED",
        db=db,
        claims=claims,
    )
