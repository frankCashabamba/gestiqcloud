import os
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import text


def _test_tenant_id() -> UUID:
    return UUID(os.getenv("TEST_TENANT_ID", "00000000-0000-0000-0000-000000000002"))


def _ensure_test_tenant(db) -> UUID:
    tenant_id = _test_tenant_id()
    row = db.execute(text("SELECT id FROM tenants WHERE id = :id"), {"id": str(tenant_id)}).first()
    if row is None:
        db.execute(
            text(
                "INSERT INTO tenants (id, name, slug, active, created_at) "
                "VALUES (:id, :name, :slug, :active, CURRENT_TIMESTAMP)"
            ),
            {"id": str(tenant_id), "name": "HR Tenant", "slug": "hr-tenant", "active": True},
        )
        db.commit()
    return tenant_id


def _employee_payload(document: str = "12345678A") -> dict:
    return {
        "sku": "EMP-001",
        "name": "Ana",
        "apellidos": "Lopez",
        "tipo_documento": "ID",
        "numero_documento": document,
        "email": "",
        "phone": "600000000",
        "fecha_ingreso": "2026-03-01",
        "departamento_id": "Operaciones",
        "puesto": "Encargada",
        "tipo_contrato": "indefinido",
        "jornada": "completa",
        "salario_base": "1800.00",
        "banco": "BBVA",
        "numero_cuenta": "ES1200000000000000000000",
        "seguridad_social": "SS-123",
        "estado": "activo",
        "notas": "Alta inicial",
    }


def test_hr_employee_crud_basic(client: TestClient, db):
    _ensure_test_tenant(db)

    created = client.post("/api/v1/tenant/hr/employees", json=_employee_payload())
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Ana"
    assert body["tipo_contrato"] == "indefinido"
    assert body["salario_base"] == "1800.00"

    employee_id = body["id"]

    listed = client.get("/api/v1/tenant/hr/employees")
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == employee_id

    updated = client.put(
        f"/api/v1/tenant/hr/employees/{employee_id}",
        json={"estado": "baja", "salario_base": "1950.00"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["estado"] == "baja"
    assert updated.json()["salario_base"] == "1950.00"


def test_hr_vacations_workflow(client: TestClient, db):
    _ensure_test_tenant(db)
    employee = client.post("/api/v1/tenant/hr/employees", json=_employee_payload("87654321B"))
    assert employee.status_code == 201, employee.text
    employee_id = employee.json()["id"]

    created = client.post(
        "/api/v1/tenant/hr/vacations",
        json={
            "empleado_id": employee_id,
            "fecha_inicio": "2026-04-10",
            "fecha_fin": "2026-04-12",
            "tipo": "vacaciones",
            "motivo": "Descanso anual",
        },
    )
    assert created.status_code == 201, created.text
    vacation = created.json()
    assert vacation["dias"] == 3
    assert vacation["estado"] == "pendiente"

    approved = client.post(f"/api/v1/tenant/hr/vacations/{vacation['id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["estado"] == "aprobada"

    listed = client.get("/api/v1/tenant/hr/vacations", params={"empleadoId": employee_id})
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["items"]) == 1


def test_hr_timekeeping_create_and_list(client: TestClient, db):
    _ensure_test_tenant(db)
    employee = client.post("/api/v1/tenant/hr/employees", json=_employee_payload("99887766C"))
    assert employee.status_code == 201, employee.text
    employee_id = employee.json()["id"]

    created = client.post(
        "/api/v1/tenant/hr/timekeeping",
        json={
            "empleado_id": employee_id,
            "fecha": "2026-03-11",
            "hora_inicio": "08:00:00",
            "hora_fin": "17:00:00",
            "tipo": "trabajo",
            "notas": "Turno completo",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["hora_inicio"] == "08:00"
    assert body["hora_fin"] == "17:00"

    listed = client.get("/api/v1/tenant/hr/timekeeping")
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["empleado_id"] == employee_id


def test_hr_payroll_generate_and_list(client: TestClient, db):
    _ensure_test_tenant(db)
    employee = client.post("/api/v1/tenant/hr/employees", json=_employee_payload("55443322D"))
    assert employee.status_code == 201, employee.text

    created = client.post(
        "/api/v1/tenant/hr/payroll/generate",
        json={
            "payroll_month": "2026-03",
            "payroll_date": "2026-03-31",
        },
    )
    assert created.status_code == 201, created.text
    payroll = created.json()
    assert payroll["payroll_month"] == "2026-03"
    assert payroll["total_employees"] == 1

    listed = client.get("/api/v1/tenant/hr/payroll")
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == payroll["id"]


def test_hr_payroll_delete_draft(client: TestClient, db):
    _ensure_test_tenant(db)
    employee = client.post("/api/v1/tenant/hr/employees", json=_employee_payload("11223344E"))
    assert employee.status_code == 201, employee.text

    created = client.post(
        "/api/v1/tenant/hr/payroll/generate",
        json={
            "payroll_month": "2026-04",
            "payroll_date": "2026-04-30",
        },
    )
    assert created.status_code == 201, created.text
    payroll_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/tenant/hr/payroll/{payroll_id}")
    assert deleted.status_code == 204, deleted.text

    listed = client.get("/api/v1/tenant/hr/payroll", params={"payrollMonth": "2026-04"})
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"] == []


def test_hr_payroll_prevents_duplicate_period(client: TestClient, db):
    _ensure_test_tenant(db)
    employee = client.post("/api/v1/tenant/hr/employees", json=_employee_payload("66778899F"))
    assert employee.status_code == 201, employee.text

    first = client.post(
        "/api/v1/tenant/hr/payroll/generate",
        json={
            "payroll_month": "2026-05",
            "payroll_date": "2026-05-31",
        },
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/tenant/hr/payroll/generate",
        json={
            "payroll_month": "2026-05",
            "payroll_date": "2026-05-31",
        },
    )
    assert second.status_code == 400, second.text
    assert "Payroll already exists" in second.text
