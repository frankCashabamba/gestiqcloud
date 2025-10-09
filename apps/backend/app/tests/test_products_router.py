from fastapi.testclient import TestClient


def _ensure_product_table():
    # Import Product model and create table in SQLite tests if missing
    from app.models.catalog.product import Product  # noqa: F401
    from app.config.database import Base, engine
    Base.metadata.create_all(bind=engine)


def test_list_routes_has_products(client: TestClient):
    paths = sorted([getattr(r, "path", "") for r in client.app.router.routes])
    assert any(p.startswith("/api/v1/products") for p in paths), "products routes not mounted"


def test_products_list_empty_ok(client: TestClient):
    _ensure_product_table()
    r = client.get("/api/v1/products")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
