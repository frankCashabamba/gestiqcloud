import secrets

from fastapi.testclient import TestClient

from app.models.core.clients import Cliente


def test_client_detail_is_scoped_to_authenticated_tenant(
    client: TestClient, db, usuario_empresa_factory
):
    password_a = secrets.token_urlsafe(12)
    password_b = secrets.token_urlsafe(12)

    _, tenant_a = usuario_empresa_factory(
        empresa_nombre="Demo Kusi",
        empresa_slug="demo-kusi",
        username="demo_kusi_clients",
        email="demo-kusi-clients@example.com",
        password=password_a,
    )
    _, tenant_b = usuario_empresa_factory(
        empresa_nombre="Otra Empresa",
        empresa_slug="otra-empresa",
        username="other_clients",
        email="other-clients@example.com",
        password=password_b,
    )

    foreign_client = Cliente(name="Cliente ajeno", tenant_id=tenant_b.id)
    db.add(foreign_client)
    db.commit()
    db.refresh(foreign_client)

    login = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": "demo_kusi_clients", "password": password_a},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.get(
        f"/api/v1/tenant/clients/{foreign_client.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_client_update_and_delete_are_scoped_to_authenticated_tenant(
    client: TestClient, db, usuario_empresa_factory
):
    password_a = secrets.token_urlsafe(12)
    password_b = secrets.token_urlsafe(12)

    _, tenant_a = usuario_empresa_factory(
        empresa_nombre="Demo Kusi",
        empresa_slug="demo-kusi",
        username="demo_kusi_clients_writer",
        email="demo-kusi-clients-writer@example.com",
        password=password_a,
    )
    _, tenant_b = usuario_empresa_factory(
        empresa_nombre="Otra Empresa",
        empresa_slug="otra-empresa",
        username="other_clients_writer",
        email="other-clients-writer@example.com",
        password=password_b,
    )

    own_client = Cliente(name="Cliente propio", tenant_id=tenant_a.id)
    foreign_client = Cliente(name="Cliente ajeno", tenant_id=tenant_b.id)
    db.add_all([own_client, foreign_client])
    db.commit()
    db.refresh(own_client)
    db.refresh(foreign_client)
    own_client_id = own_client.id
    foreign_client_id = foreign_client.id

    login = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": "demo_kusi_clients_writer", "password": password_a},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_response = client.put(
        f"/api/v1/tenant/clients/{foreign_client.id}",
        json={"name": "Hackeado"},
        headers=headers,
    )
    assert update_response.status_code == 404

    delete_response = client.delete(
        f"/api/v1/tenant/clients/{foreign_client.id}",
        headers=headers,
    )
    assert delete_response.status_code == 200

    db.expire_all()
    still_there = db.get(Cliente, foreign_client_id)
    assert still_there is not None
    assert still_there.name == "Cliente ajeno"

    own_delete = client.delete(
        f"/api/v1/tenant/clients/{own_client.id}",
        headers=headers,
    )
    assert own_delete.status_code == 200

    db.expire_all()
    assert db.get(Cliente, own_client_id) is None
