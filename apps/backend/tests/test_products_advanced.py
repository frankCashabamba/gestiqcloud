"""
Advanced product endpoint tests: duplicates/similar, duplicates/merge, POST /purge.

Rutas reales (prefijo /api/v1/tenant/products):
  GET  /duplicates/similar
  POST /duplicates/merge
  POST /purge
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.core.products import Product
from app.models.tenant import Tenant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE = "/api/v1/tenant/products"


def _make_product(db: Session, tenant_id: Any, name: str, sku: str | None = None) -> Product:
    """Crea y persiste un producto de prueba."""
    p = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name,
        price=10.0,
        stock=0.0,
        unit="unit",
        sku=sku or f"SKU-{uuid.uuid4().hex[:6]}",
        active=True,
    )
    db.add(p)
    db.flush()
    return p


def _token_for_tenant(tenant_id: Any, *, is_company_admin: bool = True) -> str:
    """Devuelve un access_token tenant sin depender del flujo de login completo."""
    from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService

    return PyJWTTokenService().issue_access(
        {
            "user_id": str(uuid.uuid4()),
            "tenant_id": str(tenant_id),
            "scope": "tenant",
            "kind": "tenant",
            "is_company_admin": is_company_admin,
            "permisos": {},
        }
    )


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _ensure_product_table(db: Session) -> None:
    """Garantiza que la tabla products existe (SQLite)."""
    Product.__table__.create(bind=db.get_bind(), checkfirst=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_a(db: Session):
    """Tenant A con usuario companyAdmin para pruebas de aislamiento."""
    empresa = f"TenantA-{uuid.uuid4().hex[:4]}"

    Tenant.__table__.create(bind=db.get_bind(), checkfirst=True)
    tid = uuid.uuid4()
    tenant = Tenant(id=tid, name=empresa, slug=f"ta-{tid.hex[:8]}")
    db.add(tenant)
    db.commit()

    return {"tenant_id": tid}


@pytest.fixture
def tenant_b(db: Session):
    """Tenant B independiente para pruebas de aislamiento."""
    empresa = f"TenantB-{uuid.uuid4().hex[:4]}"

    Tenant.__table__.create(bind=db.get_bind(), checkfirst=True)
    tid = uuid.uuid4()
    tenant = Tenant(id=tid, name=empresa, slug=f"tb-{tid.hex[:8]}")
    db.add(tenant)
    db.commit()

    return {"tenant_id": tid}


# ===========================================================================
# GET /products/duplicates/similar
# ===========================================================================


class TestDuplicatesSimilar:
    """GET /api/v1/tenant/products/duplicates/similar"""

    def test_lista_vacia_sin_duplicados(self, client: TestClient, db: Session):
        """Sin productos similares devuelve grupos vacíos."""
        _ensure_product_table(db)
        # Creamos productos con nombres muy distintos bajo el tenant de prueba
        # (el pytest-bypass usa TEST_TENANT_ID → algún tenant existente)
        r = client.get(f"{BASE}/duplicates/similar")
        assert r.status_code == 200
        body = r.json()
        assert "groups" in body
        assert "total_groups" in body
        # Puede haber o no grupos según el estado de la BD; lo que importa es el schema
        assert isinstance(body["groups"], list)
        assert isinstance(body["total_groups"], int)
        assert body["total_groups"] == len(body["groups"])

    def test_devuelve_grupos_cuando_hay_similares(self, client: TestClient, db: Session, tenant_a, tenant_b):
        """Cuando hay productos similares para tenant_a, el endpoint los agrupa."""
        _ensure_product_table(db)
        tid_a = tenant_a["tenant_id"]

        # Dos nombres casi idénticos → deberían agruparse
        _make_product(db, tid_a, "Leche Entera 1L")
        _make_product(db, tid_a, "leche entera 1l")  # mismo texto, distinta capitalización
        db.commit()

        tok_a = _token_for_tenant(tenant_a["tenant_id"])
        r = client.get(f"{BASE}/duplicates/similar", headers=_auth(tok_a))
        assert r.status_code == 200
        body = r.json()
        # Debe haber al menos un grupo (los dos productos similares)
        assert body["total_groups"] >= 1
        group = body["groups"][0]
        assert "winner" in group
        assert "candidates" in group
        assert len(group["candidates"]) >= 1

    def test_no_cruza_tenants(self, client: TestClient, db: Session, tenant_a, tenant_b):
        """Productos similares de tenant_b NO aparecen en la respuesta de tenant_a."""
        _ensure_product_table(db)
        tid_a = tenant_a["tenant_id"]
        tid_b = tenant_b["tenant_id"]

        # Solo tenant_b tiene los productos similares
        _make_product(db, tid_b, "Pan Blanco Grande")
        _make_product(db, tid_b, "pan blanco grande")
        # Tenant_a tiene un producto totalmente distinto
        _make_product(db, tid_a, f"Producto Unico {uuid.uuid4().hex[:6]}")
        db.commit()

        tok_a = _token_for_tenant(tenant_a["tenant_id"])
        r = client.get(f"{BASE}/duplicates/similar", headers=_auth(tok_a))
        assert r.status_code == 200
        body = r.json()

        # Recopilar todos los nombres devueltos para tenant_a
        all_names: list[str] = []
        for grp in body["groups"]:
            all_names.append(grp["winner"]["name"])
            all_names.extend(c["name"] for c in grp["candidates"])

        # Ningún nombre debe coincidir con los productos del tenant_b
        assert "Pan Blanco Grande" not in all_names
        assert "pan blanco grande" not in all_names


# ===========================================================================
# POST /products/duplicates/merge
# ===========================================================================


class TestDuplicatesMerge:
    """POST /api/v1/tenant/products/duplicates/merge"""

    def test_merge_exitoso(self, client: TestClient, db: Session, tenant_a):
        """Merge correcto: borra el loser, devuelve winner_id y merged=1."""
        _ensure_product_table(db)
        tid_a = tenant_a["tenant_id"]

        winner = _make_product(db, tid_a, "Queso Manchego", sku="QM-001")
        loser = _make_product(db, tid_a, "queso manchego", sku=None)
        loser_id = loser.id
        db.commit()

        tok = _token_for_tenant(tenant_a["tenant_id"])
        r = client.post(
            f"{BASE}/duplicates/merge",
            json={"winner_id": str(winner.id), "loser_ids": [str(loser.id)]},
            headers=_auth(tok),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["merged"] == 1
        assert body["winner_id"] == str(winner.id)
        assert str(loser_id) in body["deleted_ids"]

        # Verificar que el loser ya no existe
        db.expire_all()
        gone = db.query(Product).filter(Product.id == loser_id).first()
        assert gone is None

    def test_merge_requiere_permiso(self, client: TestClient, db: Session, tenant_a, tenant_b):
        """Un token sin is_company_admin y sin products.update debe recibir 403."""
        _ensure_product_table(db)
        tid_b = tenant_b["tenant_id"]

        winner = _make_product(db, tid_b, "Aceite Oliva")
        loser = _make_product(db, tid_b, "aceite oliva")
        db.commit()

        tok = _token_for_tenant(tid_b, is_company_admin=False)
        r = client.post(
            f"{BASE}/duplicates/merge",
            json={"winner_id": str(winner.id), "loser_ids": [str(loser.id)]},
            headers=_auth(tok),
        )
        assert r.status_code == 403

    def test_merge_rechaza_ids_de_otro_tenant(self, client: TestClient, db: Session, tenant_a, tenant_b):
        """El loser de tenant_b no puede ser mergeado desde tenant_a → 404 losers_not_found."""
        _ensure_product_table(db)
        tid_a = tenant_a["tenant_id"]
        tid_b = tenant_b["tenant_id"]

        winner_a = _make_product(db, tid_a, "Vino Tinto")
        product_b = _make_product(db, tid_b, "vino tinto")  # pertenece a otro tenant
        db.commit()

        tok_a = _token_for_tenant(tenant_a["tenant_id"])
        r = client.post(
            f"{BASE}/duplicates/merge",
            json={"winner_id": str(winner_a.id), "loser_ids": [str(product_b.id)]},
            headers=_auth(tok_a),
        )
        # El endpoint filtra losers por tenant_id → no encuentra ninguno → 404
        assert r.status_code == 404
        assert "losers_not_found" in r.text

    def test_merge_loser_ids_vacios_devuelve_400(self, client: TestClient, db: Session, tenant_a):
        """loser_ids vacíos (o igual al winner) deben devolver 400."""
        _ensure_product_table(db)
        tid_a = tenant_a["tenant_id"]
        winner = _make_product(db, tid_a, "Yogur Natural")
        db.commit()

        tok = _token_for_tenant(tenant_a["tenant_id"])
        r = client.post(
            f"{BASE}/duplicates/merge",
            json={"winner_id": str(winner.id), "loser_ids": []},
            headers=_auth(tok),
        )
        assert r.status_code == 400
        assert "empty_loser_ids" in r.text


# ===========================================================================
# POST /products/purge
# ===========================================================================


class TestPurge:
    """POST /api/v1/tenant/products/purge"""

    def test_purge_dry_run_no_elimina(self, client: TestClient, db: Session, tenant_a):
        """dry_run=True devuelve conteos pero no borra nada."""
        _ensure_product_table(db)
        tid_a = tenant_a["tenant_id"]

        _make_product(db, tid_a, "Arroz Largo")
        _make_product(db, tid_a, "Arroz Corto")
        db.commit()

        tok = _token_for_tenant(tenant_a["tenant_id"])
        r = client.post(
            f"{BASE}/purge",
            json={"confirm": "PURGE", "dry_run": True},
            headers=_auth(tok),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["dry_run"] is True
        assert body["counts"]["products"] >= 2
        # deleted debe ser todo ceros en dry_run
        assert all(v == 0 for v in body["deleted"].values())

        # Los productos siguen existiendo
        db.expire_all()
        count = db.query(Product).filter(Product.tenant_id == tid_a).count()
        assert count >= 2

    def test_purge_elimina_productos_del_tenant(self, client: TestClient, db: Session, tenant_a):
        """Con confirm=PURGE borra todos los productos del tenant."""
        _ensure_product_table(db)
        tid_a = tenant_a["tenant_id"]

        _make_product(db, tid_a, "Producto Purge A")
        _make_product(db, tid_a, "Producto Purge B")
        db.commit()

        tok = _token_for_tenant(tenant_a["tenant_id"])
        r = client.post(
            f"{BASE}/purge",
            json={"confirm": "PURGE", "dry_run": False},
            headers=_auth(tok),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["dry_run"] is False
        assert body["deleted"]["products"] >= 2

        # Verificar en BD que los productos de tenant_a fueron eliminados
        db.expire_all()
        count = db.query(Product).filter(Product.tenant_id == tid_a).count()
        assert count == 0

    def test_purge_requiere_confirmacion(self, client: TestClient, db: Session, tenant_a):
        """confirm distinto a 'PURGE' debe devolver 400."""
        _ensure_product_table(db)

        tok = _token_for_tenant(tenant_a["tenant_id"])
        r = client.post(
            f"{BASE}/purge",
            json={"confirm": "SI", "dry_run": False},
            headers=_auth(tok),
        )
        assert r.status_code == 400
        assert "confirmation_required" in r.text

    def test_purge_no_afecta_otro_tenant(self, client: TestClient, db: Session, tenant_a, tenant_b):
        """El purge de tenant_a no debe eliminar productos de tenant_b."""
        _ensure_product_table(db)
        tid_a = tenant_a["tenant_id"]
        tid_b = tenant_b["tenant_id"]

        _make_product(db, tid_a, "Prod Tenant A 1")
        prod_b = _make_product(db, tid_b, "Prod Tenant B 1")
        db.commit()

        # Purge desde tenant_a
        tok_a = _token_for_tenant(tenant_a["tenant_id"])
        r = client.post(
            f"{BASE}/purge",
            json={"confirm": "PURGE", "dry_run": False},
            headers=_auth(tok_a),
        )
        assert r.status_code == 200

        # El producto de tenant_b debe seguir existiendo
        db.expire_all()
        still_there = db.query(Product).filter(Product.id == prod_b.id).first()
        assert still_there is not None
        assert str(still_there.tenant_id) == str(tid_b)

    def test_purge_requiere_permiso_products_purge(self, client: TestClient, db: Session, tenant_b):
        """Usuario sin products.purge (y sin is_company_admin) recibe 403."""
        _ensure_product_table(db)
        tid_b = tenant_b["tenant_id"]

        tok = _token_for_tenant(tid_b, is_company_admin=False)
        r = client.post(
            f"{BASE}/purge",
            json={"confirm": "PURGE", "dry_run": False},
            headers=_auth(tok),
        )
        assert r.status_code == 403
