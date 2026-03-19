from __future__ import annotations

from app.models.company.company_settings import CompanySettings
from app.models.core.module import CompanyModule, Module
from app.modules.settings.application.modules_catalog import get_available_modules


def _login_headers(client, user_email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": user_email, "password": "tenant123"},
    )
    assert response.status_code == 200, response.text
    token = response.json().get("access_token")
    assert token
    return {"Authorization": f"Bearer {token}"}


def _seed_company_settings(db, tenant_id):
    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    if settings:
        return settings
    settings = CompanySettings(
        tenant_id=tenant_id,
        default_language="es",
        timezone="Europe/Madrid",
        currency="EUR",
        secondary_color="#111111",
        primary_color="#ffffff",
        settings={"enabled_modules": ["sales"], "config": {}},
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def _module_row(db, module_id: str) -> Module:
    get_available_modules(db=db)
    module = db.query(Module).filter(Module.name == module_id).first()
    assert module is not None, f"Missing module row for {module_id}"
    return module


def test_settings_modules_list_uses_company_modules_as_source_of_truth(
    client, db, usuario_empresa_factory
):
    user, tenant = usuario_empresa_factory(
        empresa_name="Empresa Settings Modules",
        username="settings_modules_admin",
        email="settings_modules_admin@example.com",
    )
    headers = _login_headers(client, user.email)
    settings = _seed_company_settings(db, tenant.id)
    finance = _module_row(db, "finance")
    inventory = _module_row(db, "inventory")

    db.add(
        CompanyModule(
            tenant_id=tenant.id,
            module_id=finance.id,
            active=True,
        )
    )
    db.add(
        CompanyModule(
            tenant_id=tenant.id,
            module_id=inventory.id,
            active=False,
        )
    )
    db.commit()

    response = client.get("/api/v1/settings/modules", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    modules = {item["id"]: item for item in payload["modules"]}

    assert set(modules) == {"finance", "inventory"}
    assert modules["finance"]["is_enabled"] is True
    assert modules["inventory"]["is_enabled"] is False

    db.refresh(settings)
    assert set(settings.settings["enabled_modules"]) == {"finance"}


def test_settings_modules_enable_disable_sync_company_modules_and_dependencies(
    client, db, usuario_empresa_factory
):
    user, tenant = usuario_empresa_factory(
        empresa_name="Empresa Settings Toggle",
        username="settings_toggle_admin",
        email="settings_toggle_admin@example.com",
    )
    headers = _login_headers(client, user.email)
    settings = _seed_company_settings(db, tenant.id)

    finance = _module_row(db, "finance")
    inventory = _module_row(db, "inventory")
    sales = _module_row(db, "sales")

    db.add(CompanyModule(tenant_id=tenant.id, module_id=finance.id, active=False))
    db.add(CompanyModule(tenant_id=tenant.id, module_id=inventory.id, active=True))
    db.add(CompanyModule(tenant_id=tenant.id, module_id=sales.id, active=True))
    db.commit()

    enable_response = client.post("/api/v1/settings/modules/finanzas/enable", headers=headers)
    assert enable_response.status_code == 200, enable_response.text
    db.refresh(settings)
    assert set(settings.settings["enabled_modules"]) == {"inventory", "sales", "finance"}

    finance_assignment = (
        db.query(CompanyModule)
        .filter(CompanyModule.tenant_id == tenant.id, CompanyModule.module_id == finance.id)
        .first()
    )
    assert finance_assignment is not None
    assert finance_assignment.active is True

    disable_response = client.post("/api/v1/settings/modules/inventory/disable", headers=headers)
    assert disable_response.status_code == 409, disable_response.text
    detail = disable_response.json()["detail"]
    assert detail["code"] == "module_has_dependents"
    assert detail["dependents"] == ["sales"]
