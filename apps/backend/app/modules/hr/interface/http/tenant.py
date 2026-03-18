"""HR Module - HTTP API (Tenant)"""

from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.company.company_settings import CompanySettings
from app.models.hr.attendance import TimeEntry, VacationRequest
from app.models.hr.employee import Employee, EmployeeSalary
from app.models.hr.payroll import Payroll, PayrollDetail
from app.models.hr.payslip import PaymentSlip
from app.models.tenant import Tenant
from app.modules.hr.application.compensation import (
    build_salary_notes,
    current_payment_mode,
    current_salary_amount,
    payment_mode_to_api,
)
from app.modules.hr.application.payroll_service import PayrollService

router = APIRouter(
    prefix="/hr",
    tags=["HR"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# SCHEMAS
# ============================================================================


class PayrollDetailResponse(BaseModel):
    """Detalle de empleado en nómina."""

    employee_id: UUID
    gross_salary: Decimal
    irpf: Decimal
    social_security: Decimal
    mutual_insurance: Decimal
    total_deductions: Decimal
    net_salary: Decimal

    class Config:
        from_attributes = True


class EmployeeBaseRequest(BaseModel):
    sku: str | None = None
    name: str
    apellidos: str
    tipo_documento: str = "ID"
    numero_documento: str
    email: str | None = None
    phone: str | None = None
    telefono: str | None = None
    fecha_nacimiento: date | None = None
    fecha_ingreso: date
    fecha_salida: date | None = None
    departamento_id: str | None = None
    puesto: str | None = None
    tipo_contrato: str = "indefinido"
    jornada: str = "completa"
    modalidad_pago: str = "mensual"
    salario_base: Decimal
    banco: str | None = None
    numero_cuenta: str | None = None
    seguridad_social: str | None = None
    estado: str = "activo"
    notas: str | None = None


class EmployeeCreateRequest(EmployeeBaseRequest):
    pass


class EmployeeUpdateRequest(BaseModel):
    sku: str | None = None
    name: str | None = None
    apellidos: str | None = None
    tipo_documento: str | None = None
    numero_documento: str | None = None
    email: str | None = None
    phone: str | None = None
    telefono: str | None = None
    fecha_nacimiento: date | None = None
    fecha_ingreso: date | None = None
    fecha_salida: date | None = None
    departamento_id: str | None = None
    puesto: str | None = None
    tipo_contrato: str | None = None
    jornada: str | None = None
    modalidad_pago: str | None = None
    salario_base: Decimal | None = None
    banco: str | None = None
    numero_cuenta: str | None = None
    seguridad_social: str | None = None
    estado: str | None = None
    notas: str | None = None


class EmployeeResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    sku: str | None = None
    codigo: str | None = None
    name: str
    apellidos: str
    tipo_documento: str
    numero_documento: str
    email: str | None = None
    phone: str | None = None
    telefono: str | None = None
    fecha_nacimiento: date | None = None
    fecha_ingreso: date
    fecha_salida: date | None = None
    departamento_id: str | None = None
    puesto: str | None = None
    tipo_contrato: str
    jornada: str
    modalidad_pago: str
    salario_base: Decimal
    banco: str | None = None
    numero_cuenta: str | None = None
    seguridad_social: str | None = None
    estado: str
    notas: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]


class VacationCreateRequest(BaseModel):
    empleado_id: UUID
    fecha_inicio: date
    fecha_fin: date
    dias: int | None = None
    tipo: str = "vacaciones"
    motivo: str | None = None
    notas: str | None = None


class VacationRejectRequest(BaseModel):
    motivo: str | None = None


class VacationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    empleado_id: UUID
    fecha_inicio: date
    fecha_fin: date
    dias: int
    tipo: str
    estado: str
    motivo: str | None = None
    notas: str | None = None
    aprobado_por: UUID | None = None
    fecha_aprobacion: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VacationListResponse(BaseModel):
    items: list[VacationResponse]


class TimeEntryCreateRequest(BaseModel):
    empleado_id: UUID
    fecha: date
    hora_inicio: time
    hora_fin: time | None = None
    tipo: str = "trabajo"
    notas: str | None = None


class TimeEntryUpdateRequest(BaseModel):
    hora_inicio: time | None = None
    hora_fin: time | None = None
    tipo: str | None = None
    notas: str | None = None


class TimeEntryResponse(BaseModel):
    id: UUID
    empleado_id: UUID
    fecha: date
    hora_inicio: str
    hora_fin: str | None = None
    tipo: str
    notas: str | None = None


class TimeEntryListResponse(BaseModel):
    items: list[TimeEntryResponse]


class PayrollResponse(BaseModel):
    """Respuesta de nómina."""

    id: UUID
    payroll_month: str
    payroll_date: date
    status: str
    total_employees: int
    total_gross: Decimal
    total_irpf: Decimal
    total_social_security_employee: Decimal
    total_social_security_employer: Decimal
    total_deductions: Decimal
    total_net: Decimal
    details: list[PayrollDetailResponse] | None = None

    class Config:
        from_attributes = True


class PayrollListResponse(BaseModel):
    items: list[PayrollResponse]


class PayrollCreateRequest(BaseModel):
    """Solicitud para generar nómina."""

    payroll_month: str  # "2026-02"
    payroll_date: date


class PaymentSlipResponse(BaseModel):
    """Respuesta de boleta de pago."""

    id: UUID
    employee_id: UUID
    status: str
    sent_at: date | None = None
    viewed_at: date | None = None
    valid_until: date
    download_count: int

    class Config:
        from_attributes = True


STATUS_TO_MODEL = {
    "activo": "ACTIVE",
    "baja": "TERMINATED",
    "suspendido": "INACTIVE",
}
STATUS_FROM_MODEL = {value: key for key, value in STATUS_TO_MODEL.items()}
STATUS_FROM_MODEL.setdefault("ON_LEAVE", "suspendido")

CONTRACT_TO_MODEL = {
    "indefinido": "PERMANENT",
    "temporal": "TEMPORARY",
    "parcial": "PART_TIME",
    "practicas": "APPRENTICE",
    "formacion": "APPRENTICE",
    "autonomo": "CONTRACTOR",
}
CONTRACT_FROM_MODEL = {
    "PERMANENT": "indefinido",
    "TEMPORARY": "temporal",
    "PART_TIME": "parcial",
    "APPRENTICE": "practicas",
    "CONTRACTOR": "autonomo",
}


def _employee_status_to_model(value: str | None) -> str:
    return STATUS_TO_MODEL.get((value or "").lower(), "ACTIVE")


def _employee_status_from_model(value: str | None) -> str:
    return STATUS_FROM_MODEL.get(value or "", "activo")


def _contract_type_to_model(value: str | None) -> str:
    return CONTRACT_TO_MODEL.get((value or "").lower(), "PERMANENT")


def _contract_type_from_model(value: str | None) -> str:
    return CONTRACT_FROM_MODEL.get(value or "", "indefinido")


def _serialize_employee(employee: Employee) -> EmployeeResponse:
    return EmployeeResponse(
        id=employee.id,
        tenant_id=employee.tenant_id,
        sku=employee.employee_code,
        codigo=employee.employee_code,
        name=employee.first_name,
        apellidos=employee.last_name,
        tipo_documento=employee.document_type or "ID",
        numero_documento=employee.national_id,
        email=employee.email,
        phone=employee.phone,
        telefono=employee.phone,
        fecha_nacimiento=employee.birth_date,
        fecha_ingreso=employee.hire_date,
        fecha_salida=employee.termination_date,
        departamento_id=employee.department,
        puesto=employee.job_title,
        tipo_contrato=_contract_type_from_model(employee.contract_type),
        jornada=employee.work_schedule or "completa",
        modalidad_pago=payment_mode_to_api(current_payment_mode(employee)),
        salario_base=current_salary_amount(employee),
        banco=employee.bank_name,
        numero_cuenta=employee.bank_account,
        seguridad_social=employee.social_security_number,
        estado=_employee_status_from_model(employee.status),
        notas=employee.notes,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
    )


def _serialize_vacation(vacation: VacationRequest) -> VacationResponse:
    return VacationResponse(
        id=vacation.id,
        tenant_id=vacation.tenant_id,
        empleado_id=vacation.employee_id,
        fecha_inicio=vacation.start_date,
        fecha_fin=vacation.end_date,
        dias=vacation.days,
        tipo=vacation.request_type,
        estado=vacation.status,
        motivo=vacation.reason,
        notas=vacation.notes,
        aprobado_por=vacation.approved_by,
        fecha_aprobacion=vacation.approved_at,
        created_at=vacation.created_at,
        updated_at=vacation.updated_at,
    )


def _serialize_time_entry(entry: TimeEntry) -> TimeEntryResponse:
    return TimeEntryResponse(
        id=entry.id,
        empleado_id=entry.employee_id,
        fecha=entry.entry_date,
        hora_inicio=entry.clock_in_time.strftime("%H:%M"),
        hora_fin=entry.clock_out_time.strftime("%H:%M") if entry.clock_out_time else None,
        tipo=entry.entry_type,
        notas=entry.notes,
    )


def _serialize_payroll(
    payroll: Payroll, details: list[PayrollDetail] | None = None
) -> PayrollResponse:
    return PayrollResponse(
        id=payroll.id,
        payroll_month=payroll.payroll_month,
        payroll_date=payroll.payroll_date,
        status=payroll.status,
        total_employees=payroll.total_employees,
        total_gross=payroll.total_gross,
        total_irpf=payroll.total_irpf,
        total_social_security_employee=payroll.total_social_security_employee,
        total_social_security_employer=payroll.total_social_security_employer,
        total_deductions=payroll.total_deductions,
        total_net=payroll.total_net,
        details=(
            [
                PayrollDetailResponse(
                    employee_id=item.employee_id,
                    gross_salary=item.gross_salary,
                    irpf=item.irpf,
                    social_security=item.social_security,
                    mutual_insurance=item.mutual_insurance,
                    total_deductions=item.total_deductions,
                    net_salary=item.net_salary,
                )
                for item in details
            ]
            if details is not None
            else None
        ),
    )


def _days_between(start: date, end: date) -> int:
    return ((end - start).days) + 1


def _as_uuid(value: UUID | str | int | None) -> UUID | None:
    if value is None or isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _same_identifier(left: UUID | str | int | None, right: UUID | str | int | None) -> bool:
    left_uuid = _as_uuid(left)
    right_uuid = _as_uuid(right)
    if left_uuid and right_uuid:
        return left_uuid == right_uuid
    if left is None or right is None:
        return False
    return str(left) == str(right)


def _db_tenant_id(value: UUID | str | int | None) -> str | None:
    if value is None:
        return None
    parsed = _as_uuid(value)
    return str(parsed or value)


def _tenant_country_code(db: Session, tenant_id: UUID) -> str:
    tenant = (
        db.execute(select(Tenant).where(Tenant.id == _db_tenant_id(tenant_id))).scalars().first()
    )
    if tenant and tenant.country_code:
        return str(tenant.country_code).strip().upper()
    if tenant and tenant.country:
        raw = str(tenant.country).strip().upper()
        return raw if len(raw) == 2 else "ES"
    return "ES"


def _tenant_currency(db: Session, tenant_id: UUID) -> str:
    company_settings = (
        db.execute(
            select(CompanySettings).where(CompanySettings.tenant_id == _db_tenant_id(tenant_id))
        )
        .scalars()
        .first()
    )
    if company_settings and company_settings.currency:
        return str(company_settings.currency).strip().upper()
    tenant = (
        db.execute(select(Tenant).where(Tenant.id == _db_tenant_id(tenant_id))).scalars().first()
    )
    if tenant and tenant.base_currency:
        return str(tenant.base_currency).strip().upper()
    return "EUR"


# ============================================================================
# ENDPOINTS
# ============================================================================


class MeEmployeeResponse(BaseModel):
    """Perfil de empleado del usuario autenticado."""

    id: UUID
    name: str
    apellidos: str
    puesto: str | None = None
    departamento_id: str | None = None
    estado: str
    fecha_ingreso: date
    email: str | None = None
    salario_base: Decimal | None = None
    modalidad_pago: str | None = None
    tipo_contrato: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MyPayrollEntryResponse(BaseModel):
    """Entrada de nómina del empleado autenticado."""

    payroll_detail_id: UUID
    payroll_id: UUID
    payroll_month: str
    payroll_date: date
    status: str
    gross_salary: Decimal
    irpf: Decimal
    social_security: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    currency: str

    model_config = ConfigDict(from_attributes=True)


class MyPayrollListResponse(BaseModel):
    items: list[MyPayrollEntryResponse]


@router.get("/me", response_model=MeEmployeeResponse)
async def get_my_employee_profile(
    request: Request,
    db: Session = Depends(get_db),
):
    """Devuelve el perfil de empleado del usuario autenticado (lookup por email)."""
    claims = getattr(request.state, "access_claims", {}) or {}
    user_email = claims.get("sub") or claims.get("email")
    tenant_id = claims.get("tenant_id")

    if not user_email or not tenant_id:
        raise HTTPException(status_code=401, detail="unauthenticated")

    try:
        tid = UUID(str(tenant_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="invalid_tenant")

    employee = (
        db.execute(
            select(Employee).where(
                Employee.tenant_id == tid,
                Employee.email == str(user_email).lower(),
            )
        )
        .scalars()
        .first()
    )

    if not employee:
        raise HTTPException(status_code=404, detail="employee_not_found")

    return MeEmployeeResponse(
        id=employee.id,
        name=employee.first_name,
        apellidos=employee.last_name,
        puesto=employee.job_title,
        departamento_id=employee.department,
        estado=_employee_status_from_model(employee.status),
        fecha_ingreso=employee.hire_date,
        email=employee.email,
        salario_base=current_salary_amount(employee),
        modalidad_pago=payment_mode_to_api(current_payment_mode(employee)),
        tipo_contrato=_contract_type_from_model(employee.contract_type),
    )


@router.get("/me/payroll", response_model=MyPayrollListResponse)
async def get_my_payroll(
    request: Request,
    db: Session = Depends(get_db),
):
    """Devuelve las entradas de nómina del empleado autenticado."""
    claims = getattr(request.state, "access_claims", {}) or {}
    user_email = claims.get("sub") or claims.get("email")
    tenant_id = claims.get("tenant_id")

    if not user_email or not tenant_id:
        raise HTTPException(status_code=401, detail="unauthenticated")

    try:
        tid = UUID(str(tenant_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="invalid_tenant")

    employee = (
        db.execute(
            select(Employee).where(
                Employee.tenant_id == tid,
                Employee.email == str(user_email).lower(),
            )
        )
        .scalars()
        .first()
    )

    if not employee:
        raise HTTPException(status_code=404, detail="employee_not_found")

    rows = db.execute(
        select(PayrollDetail, Payroll)
        .join(Payroll, Payroll.id == PayrollDetail.payroll_id)
        .where(
            PayrollDetail.employee_id == employee.id,
            Payroll.tenant_id == _db_tenant_id(tid),
            Payroll.status.in_(["CONFIRMED", "PAID"]),
        )
        .order_by(Payroll.payroll_month.desc())
    ).all()

    items = [
        MyPayrollEntryResponse(
            payroll_detail_id=detail.id,
            payroll_id=payroll.id,
            payroll_month=payroll.payroll_month,
            payroll_date=payroll.payroll_date,
            status=payroll.status,
            gross_salary=detail.gross_salary,
            irpf=detail.irpf,
            social_security=detail.social_security,
            total_deductions=detail.total_deductions,
            net_salary=detail.net_salary,
            currency=detail.currency,
        )
        for detail, payroll in rows
    ]

    return MyPayrollListResponse(items=items)


@router.get("/employees", response_model=EmployeeListResponse)
async def list_employees(
    search: str | None = None,
    estado: str | None = None,
    departamento_id: str | None = Query(default=None, alias="departmentId"),
    active: bool | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> EmployeeListResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    query = select(Employee).where(Employee.tenant_id == _db_tenant_id(tenant_id))
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            Employee.first_name.ilike(term)
            | Employee.last_name.ilike(term)
            | Employee.national_id.ilike(term)
            | Employee.employee_code.ilike(term)
        )
    if estado:
        query = query.where(Employee.status == _employee_status_to_model(estado))
    elif active is True:
        query = query.where(Employee.status == "ACTIVE")
    elif active is False:
        query = query.where(Employee.status != "ACTIVE")
    if departamento_id:
        query = query.where(Employee.department == departamento_id)
    employees = db.execute(query.order_by(Employee.created_at.desc())).scalars().unique().all()
    return EmployeeListResponse(items=[_serialize_employee(employee) for employee in employees])


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> EmployeeResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    employee = db.get(Employee, employee_id)
    if not employee or not _same_identifier(employee.tenant_id, tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return _serialize_employee(employee)


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    request: EmployeeCreateRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> EmployeeResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    user_id = _as_uuid(claims.get("user_id"))
    country_code = _tenant_country_code(db, tenant_id)
    currency = _tenant_currency(db, tenant_id)
    employee = Employee(
        tenant_id=_db_tenant_id(tenant_id),
        employee_code=request.sku,
        first_name=request.name,
        last_name=request.apellidos,
        document_type=request.tipo_documento,
        national_id=request.numero_documento,
        email=request.email,
        phone=request.phone or request.telefono,
        birth_date=request.fecha_nacimiento,
        contract_type=_contract_type_to_model(request.tipo_contrato),
        status=_employee_status_to_model(request.estado),
        hire_date=request.fecha_ingreso,
        termination_date=request.fecha_salida,
        department=request.departamento_id,
        job_title=request.puesto,
        work_schedule=request.jornada,
        bank_account=request.numero_cuenta,
        bank_name=request.banco,
        social_security_number=request.seguridad_social,
        notes=request.notas,
        country=country_code,
    )
    db.add(employee)
    db.flush()
    salary = EmployeeSalary(
        employee_id=employee.id,
        salary_amount=request.salario_base,
        currency=currency,
        effective_date=request.fecha_ingreso,
        notes=build_salary_notes(request.modalidad_pago),
        created_by=user_id,
        created_at=datetime.now(UTC),
    )
    db.add(salary)
    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


@router.put("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: UUID,
    request: EmployeeUpdateRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> EmployeeResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    user_id = _as_uuid(claims.get("user_id"))
    currency = _tenant_currency(db, tenant_id)
    employee = db.get(Employee, employee_id)
    if not employee or not _same_identifier(employee.tenant_id, tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    payload = request.model_dump(exclude_unset=True)
    if "sku" in payload:
        employee.employee_code = payload["sku"]
    if "name" in payload:
        employee.first_name = payload["name"]
    if "apellidos" in payload:
        employee.last_name = payload["apellidos"]
    if "tipo_documento" in payload:
        employee.document_type = payload["tipo_documento"]
    if "numero_documento" in payload:
        employee.national_id = payload["numero_documento"]
    if "email" in payload:
        employee.email = payload["email"]
    if "phone" in payload or "telefono" in payload:
        employee.phone = payload.get("phone") or payload.get("telefono")
    if "fecha_nacimiento" in payload:
        employee.birth_date = payload["fecha_nacimiento"]
    if "fecha_ingreso" in payload:
        employee.hire_date = payload["fecha_ingreso"]
    if "fecha_salida" in payload:
        employee.termination_date = payload["fecha_salida"]
    if "departamento_id" in payload:
        employee.department = payload["departamento_id"]
    if "puesto" in payload:
        employee.job_title = payload["puesto"]
    if "tipo_contrato" in payload:
        employee.contract_type = _contract_type_to_model(payload["tipo_contrato"])
    if "jornada" in payload:
        employee.work_schedule = payload["jornada"]
    if "banco" in payload:
        employee.bank_name = payload["banco"]
    if "numero_cuenta" in payload:
        employee.bank_account = payload["numero_cuenta"]
    if "seguridad_social" in payload:
        employee.social_security_number = payload["seguridad_social"]
    if "estado" in payload:
        employee.status = _employee_status_to_model(payload["estado"])
    if "notas" in payload:
        employee.notes = payload["notas"]

    if "salario_base" in payload or "modalidad_pago" in payload:
        current_salary = current_salary_amount(employee)
        current_mode = payment_mode_to_api(current_payment_mode(employee))
        next_salary = (
            Decimal(str(payload["salario_base"]))
            if payload.get("salario_base") is not None
            else current_salary
        )
        next_mode = payload.get("modalidad_pago") or current_mode
        if next_salary != current_salary or next_mode != current_mode:
            db.add(
                EmployeeSalary(
                    employee_id=employee.id,
                    salary_amount=next_salary,
                    currency=currency,
                    effective_date=date.today(),
                    notes=build_salary_notes(next_mode),
                    created_by=user_id,
                    created_at=datetime.now(UTC),
                )
            )

    db.commit()
    db.refresh(employee)
    return _serialize_employee(employee)


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> None:
    tenant_id = _as_uuid(claims["tenant_id"])
    employee = db.get(Employee, employee_id)
    if not employee or not _same_identifier(employee.tenant_id, tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    db.delete(employee)
    db.commit()


@router.get("/vacations", response_model=VacationListResponse)
async def list_vacations(
    empleadoId: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    startDate: date | None = None,
    endDate: date | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> VacationListResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    query = select(VacationRequest).where(VacationRequest.tenant_id == _db_tenant_id(tenant_id))
    if empleadoId:
        query = query.where(VacationRequest.employee_id == empleadoId)
    if status_filter:
        query = query.where(VacationRequest.status == status_filter)
    if startDate:
        query = query.where(VacationRequest.start_date >= startDate)
    if endDate:
        query = query.where(VacationRequest.end_date <= endDate)
    vacations = db.execute(query.order_by(VacationRequest.start_date.desc())).scalars().all()
    return VacationListResponse(items=[_serialize_vacation(item) for item in vacations])


@router.get("/vacations/{vacation_id}", response_model=VacationResponse)
async def get_vacation(
    vacation_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> VacationResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    vacation = db.get(VacationRequest, vacation_id)
    if not vacation or not _same_identifier(vacation.tenant_id, tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacation not found")
    return _serialize_vacation(vacation)


@router.post("/vacations", response_model=VacationResponse, status_code=status.HTTP_201_CREATED)
async def create_vacation(
    request: VacationCreateRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> VacationResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    employee = db.get(Employee, request.empleado_id)
    if not employee or not _same_identifier(employee.tenant_id, tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    if request.fecha_fin < request.fecha_inicio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid dates")
    vacation = VacationRequest(
        tenant_id=_db_tenant_id(tenant_id),
        employee_id=request.empleado_id,
        start_date=request.fecha_inicio,
        end_date=request.fecha_fin,
        days=request.dias or _days_between(request.fecha_inicio, request.fecha_fin),
        request_type=request.tipo,
        reason=request.motivo,
        notes=request.notas,
        status="pendiente",
    )
    db.add(vacation)
    db.commit()
    db.refresh(vacation)
    return _serialize_vacation(vacation)


@router.post("/vacations/{vacation_id}/approve", response_model=VacationResponse)
async def approve_vacation(
    vacation_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> VacationResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    vacation = db.get(VacationRequest, vacation_id)
    if not vacation or not _same_identifier(vacation.tenant_id, tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacation not found")
    vacation.status = "aprobada"
    vacation.approved_by = _as_uuid(claims.get("user_id"))
    vacation.approved_at = datetime.now(UTC)
    vacation.rejection_reason = None
    db.commit()
    db.refresh(vacation)
    return _serialize_vacation(vacation)


@router.post("/vacations/{vacation_id}/reject", response_model=VacationResponse)
async def reject_vacation(
    vacation_id: UUID,
    request: VacationRejectRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> VacationResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    vacation = db.get(VacationRequest, vacation_id)
    if not vacation or not _same_identifier(vacation.tenant_id, tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacation not found")
    vacation.status = "rechazada"
    vacation.approved_by = _as_uuid(claims.get("user_id"))
    vacation.approved_at = datetime.now(UTC)
    vacation.rejection_reason = request.motivo
    db.commit()
    db.refresh(vacation)
    return _serialize_vacation(vacation)


@router.get("/timekeeping", response_model=TimeEntryListResponse)
async def list_time_entries(
    empleadoId: UUID | None = None,
    fromDate: date | None = None,
    toDate: date | None = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> TimeEntryListResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    query = select(TimeEntry).where(TimeEntry.tenant_id == _db_tenant_id(tenant_id))
    if empleadoId:
        query = query.where(TimeEntry.employee_id == empleadoId)
    if fromDate:
        query = query.where(TimeEntry.entry_date >= fromDate)
    if toDate:
        query = query.where(TimeEntry.entry_date <= toDate)
    entries = (
        db.execute(
            query.order_by(
                TimeEntry.entry_date.desc(),
                TimeEntry.clock_in_time.desc(),
                TimeEntry.created_at.desc(),
            )
        )
        .scalars()
        .all()
    )
    return TimeEntryListResponse(items=[_serialize_time_entry(item) for item in entries])


@router.post("/timekeeping", response_model=TimeEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_time_entry(
    request: TimeEntryCreateRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> TimeEntryResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    employee = db.get(Employee, request.empleado_id)
    if not employee or not _same_identifier(employee.tenant_id, tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    if request.hora_fin and request.hora_fin < request.hora_inicio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid time range")
    if request.hora_fin is None:
        open_entry = (
            db.execute(
                select(TimeEntry).where(
                    TimeEntry.tenant_id == _db_tenant_id(tenant_id),
                    TimeEntry.employee_id == request.empleado_id,
                    TimeEntry.clock_out_time.is_(None),
                )
            )
            .scalars()
            .first()
        )
        if open_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee already has an open time entry",
            )
    entry = TimeEntry(
        tenant_id=_db_tenant_id(tenant_id),
        employee_id=request.empleado_id,
        entry_date=request.fecha,
        clock_in_time=request.hora_inicio,
        clock_out_time=request.hora_fin,
        entry_type=request.tipo,
        notes=request.notas,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _serialize_time_entry(entry)


@router.patch("/timekeeping/{entry_id}", response_model=TimeEntryResponse)
async def update_time_entry(
    entry_id: UUID,
    request: TimeEntryUpdateRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> TimeEntryResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    entry = db.get(TimeEntry, entry_id)
    if not entry or not _same_identifier(entry.tenant_id, tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time entry not found")

    payload = request.model_dump(exclude_unset=True)
    next_clock_in = payload.get("hora_inicio", entry.clock_in_time)
    next_clock_out = payload.get("hora_fin", entry.clock_out_time)
    if next_clock_out and next_clock_out < next_clock_in:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid time range")

    if "hora_inicio" in payload:
        entry.clock_in_time = payload["hora_inicio"]
    if "hora_fin" in payload:
        entry.clock_out_time = payload["hora_fin"]
    if "tipo" in payload and payload["tipo"] is not None:
        entry.entry_type = payload["tipo"]
    if "notas" in payload:
        entry.notes = payload["notas"]

    db.commit()
    db.refresh(entry)
    return _serialize_time_entry(entry)


@router.post(
    "/payroll/generate", response_model=PayrollResponse, status_code=status.HTTP_201_CREATED
)
async def generate_payroll(
    request: PayrollCreateRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> PayrollResponse:
    """
    Genera nómina para el mes.

    Body:
    {
        "payroll_month": "2026-02",
        "payroll_date": "2026-02-28"
    }
    """
    tenant_id = _as_uuid(claims["tenant_id"])

    try:
        payroll = PayrollService.generate_payroll(
            db, tenant_id, request.payroll_month, request.payroll_date
        )

        db.commit()
        db.refresh(payroll)

        return _serialize_payroll(payroll)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/payroll", response_model=PayrollListResponse)
async def list_payrolls(
    payroll_month: str | None = Query(default=None, alias="payrollMonth"),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> PayrollListResponse:
    tenant_id = _as_uuid(claims["tenant_id"])
    query = select(Payroll).where(Payroll.tenant_id == _db_tenant_id(tenant_id))
    if payroll_month:
        query = query.where(Payroll.payroll_month == payroll_month)
    if status_filter:
        query = query.where(Payroll.status == status_filter)
    payrolls = (
        db.execute(query.order_by(Payroll.payroll_month.desc(), Payroll.created_at.desc()))
        .scalars()
        .all()
    )
    return PayrollListResponse(items=[_serialize_payroll(item) for item in payrolls])


@router.get("/payroll/{payroll_id}", response_model=PayrollResponse)
async def get_payroll(
    payroll_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> PayrollResponse:
    """Obtiene detalle completo de nómina."""
    tenant_id = _as_uuid(claims["tenant_id"])

    payroll = db.get(Payroll, payroll_id)
    if not payroll or not _same_identifier(payroll.tenant_id, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll not found",
        )

    # Cargar detalles
    details = db.query(PayrollDetail).filter_by(payroll_id=payroll_id).all()

    return _serialize_payroll(payroll, details)


@router.post("/payroll/{payroll_id}/confirm", response_model=PayrollResponse)
async def confirm_payroll(
    payroll_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> PayrollResponse:
    """Confirma nómina (DRAFT → CONFIRMED)."""
    tenant_id = _as_uuid(claims["tenant_id"])
    user_id = _as_uuid(claims.get("user_id"))

    payroll = db.get(Payroll, payroll_id)
    if not payroll or not _same_identifier(payroll.tenant_id, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll not found",
        )

    try:
        payroll = PayrollService.confirm_payroll(db, payroll_id, user_id)
        db.commit()

        return _serialize_payroll(payroll)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/payroll/{payroll_id}/mark-paid", response_model=PayrollResponse)
async def mark_payroll_paid(
    payroll_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> PayrollResponse:
    """Marca nómina como pagada (CONFIRMED → PAID)."""
    tenant_id = _as_uuid(claims["tenant_id"])

    payroll = db.get(Payroll, payroll_id)
    if not payroll or not _same_identifier(payroll.tenant_id, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll not found",
        )

    try:
        payroll = PayrollService.mark_payroll_paid(db, payroll_id)
        db.commit()

        return _serialize_payroll(payroll)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/payroll/{payroll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payroll(
    payroll_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> None:
    """Elimina una nómina en borrador."""
    tenant_id = _as_uuid(claims["tenant_id"])

    payroll = db.get(Payroll, payroll_id)
    if not payroll or not _same_identifier(payroll.tenant_id, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll not found",
        )

    try:
        PayrollService.delete_payroll(db, payroll_id)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/payroll/{payroll_detail_id}/payslip", response_model=PaymentSlipResponse)
async def get_payslip(
    payroll_detail_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> PaymentSlipResponse:
    """Obtiene información de boleta de pago."""
    tenant_id = _as_uuid(claims["tenant_id"])

    payslip = (
        db.query(PaymentSlip)
        .filter_by(
            payroll_detail_id=payroll_detail_id,
            tenant_id=_db_tenant_id(tenant_id),
        )
        .first()
    )

    if not payslip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment slip not found",
        )

    return PaymentSlipResponse(
        id=payslip.id,
        employee_id=payslip.employee_id,
        status=payslip.status,
        sent_at=payslip.sent_at,
        viewed_at=payslip.viewed_at,
        valid_until=payslip.valid_until,
        download_count=payslip.download_count,
    )


@router.get("/payroll/{payroll_detail_id}/payslip/download")
async def download_payslip(
    payroll_detail_id: UUID,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    """Descarga PDF de boleta."""
    tenant_id = _as_uuid(claims["tenant_id"])

    payslip = (
        db.query(PaymentSlip)
        .filter_by(
            payroll_detail_id=payroll_detail_id,
            tenant_id=_db_tenant_id(tenant_id),
        )
        .first()
    )

    if not payslip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment slip not found",
        )

    if not payslip.pdf_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF not yet generated",
        )

    # Registrar descarga
    payslip.download_count += 1
    from datetime import datetime

    payslip.last_download_at = datetime.now(UTC)
    if not payslip.viewed_at:
        payslip.viewed_at = datetime.now(UTC)
    db.commit()

    return {
        "filename": f"payslip_{payroll_detail_id}.pdf",
        "content_type": "application/pdf",
        "size": len(payslip.pdf_content),
    }
