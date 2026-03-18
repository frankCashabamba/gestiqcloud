from app.models.tenant import Tenant


def _admin_headers(client, superuser_factory) -> dict[str, str]:
    password = "admin123!"
    user = superuser_factory(
        username="flagsadmin",
        email="flagsadmin@example.com",
        password=password,
    )
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"identificador": user.username, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_feature_flags_reads_and_updates_tenant_overrides(
    client,
    db,
    superuser_factory,
    tenant_minimal,
):
    tenant_id = tenant_minimal["tenant_id"]
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    assert tenant is not None
    tenant.country_code = "ES"
    tenant.config_json = {
        "features": {
            "crm_enabled": True,
            "billing_enabled": False,
        }
    }
    db.commit()

    headers = _admin_headers(client, superuser_factory)

    response = client.get(f"/api/v1/admin/companies/{tenant_id}/feature-flags", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["tenant_overrides"]["crm_enabled"] is True
    assert payload["tenant_overrides"]["billing_enabled"] is False
    assert payload["flags"]["crm_enabled"] is True
    assert payload["flags"]["billing_enabled"] is False
    assert payload["source"]["crm_enabled"].startswith("tenant:")

    updated = client.put(
        f"/api/v1/admin/companies/{tenant_id}/feature-flags",
        headers=headers,
        json={"overrides": {"crm_enabled": None, "production_enabled": True}},
    )
    assert updated.status_code == 200, updated.text
    updated_payload = updated.json()
    assert "crm_enabled" not in updated_payload["tenant_overrides"]
    assert updated_payload["tenant_overrides"]["production_enabled"] is True
    assert updated_payload["flags"]["production_enabled"] is True
    assert updated_payload["source"]["production_enabled"].startswith("tenant:")

    db.refresh(tenant)
    assert tenant.config_json["features"]["production_enabled"] is True
    assert "crm_enabled" not in tenant.config_json["features"]
