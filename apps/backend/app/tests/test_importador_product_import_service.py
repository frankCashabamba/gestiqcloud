from uuid import uuid4

from app.models.core.products import Product
from app.models.tenant import Tenant
from app.modules.importador import product_import_service
from app.modules.importador.product_import_service import (
    ProductCandidate,
    build_product_candidates,
    looks_like_product_document,
    save_product_candidates,
)


def test_build_product_candidates_from_registro_rows_skips_summary_rows():
    datos = {
        "filas_por_hoja": {
            "REGISTRO": [
                {
                    "PRODUCTO": "PAN",
                    "CANTIDAD": None,
                    "PRECIO UNITARIO VENTA": None,
                    "SOBRANTE DIARIO": None,
                    "VENTA DIARIA": None,
                    "TOTAL": 108.39,
                    "col_7": "TOTAL",
                },
                {
                    "PRODUCTO": "tapados",
                    "CANTIDAD": 292,
                    "PRECIO UNITARIO VENTA": 0.13,
                    "SOBRANTE DIARIO": 52,
                    "VENTA DIARIA": 240,
                    "TOTAL": 31.2,
                },
                {
                    "PRODUCTO": "empanadas",
                    "CANTIDAD": 72,
                    "PRECIO UNITARIO VENTA": 0.2,
                    "SOBRANTE DIARIO": 0,
                    "VENTA DIARIA": 72,
                    "TOTAL": 14.4,
                },
            ]
        }
    }

    candidates, sheet_name = build_product_candidates(
        datos,
        sheet_name="REGISTRO",
        row_indexes=[0, 1, 2],
        default_category_name="Panaderia",
    )

    assert sheet_name == "REGISTRO"
    assert [candidate.name for candidate in candidates] == ["tapados", "empanadas"]
    assert candidates[0].price == 0.13
    assert candidates[0].stock == 292.0
    assert candidates[0].category_name == "Panaderia"


def test_build_product_candidates_uses_stock_and_category_columns_when_available():
    datos = {
        "filas_por_hoja": {
            "LECHE": [
                {
                    "Producto": "Leche entera",
                    "Stock": 12,
                    "Precio": 0.95,
                    "Categoria": "Lacteos",
                }
            ]
        }
    }

    candidates, sheet_name = build_product_candidates(datos, sheet_name="LECHE", row_indexes=[0])

    assert sheet_name == "LECHE"
    assert len(candidates) == 1
    assert candidates[0].name == "Leche entera"
    assert candidates[0].price == 0.95
    assert candidates[0].stock == 12.0
    assert candidates[0].category_name == "Lacteos"


def test_build_product_candidates_rejects_generic_name_only_tables():
    datos = {
        "filas_por_hoja": {
            "PERSONAL": [
                {"Nombre": "Ana Perez", "Departamento": "Ventas"},
                {"Nombre": "Luis Gomez", "Departamento": "Compras"},
            ]
        }
    }

    candidates, sheet_name = build_product_candidates(
        datos, sheet_name="PERSONAL", row_indexes=[0, 1]
    )

    assert sheet_name == "PERSONAL"
    assert candidates == []


def test_build_product_candidates_supports_runtime_detection_config():
    datos = {
        "filas_por_hoja": {
            "ARTICULOS": [
                {
                    "Articulo": "Harina premium",
                    "PVP": 42.9,
                    "Existencia": 50,
                }
            ]
        }
    }

    candidates, sheet_name = build_product_candidates(
        datos,
        sheet_name="ARTICULOS",
        row_indexes=[0],
        detection_config={
            "summary_names": ["total", "subtotal"],
            "name_keywords": ["articulo"],
            "price_keywords": ["pvp"],
            "price_reject_keywords": ["total"],
            "cost_keywords": ["costo"],
            "sku_keywords": ["sku"],
            "category_keywords": ["categoria"],
            "description_keywords": ["descripcion"],
            "explicit_stock_keywords": ["existencia"],
            "ambiguous_stock_keywords": ["cantidad"],
            "operational_keywords": ["venta"],
            "sheet_hint_keywords": ["articulos"],
        },
    )

    assert sheet_name == "ARTICULOS"
    assert len(candidates) == 1
    assert candidates[0].name == "Harina premium"
    assert candidates[0].price == 42.9
    assert candidates[0].stock == 50.0


def test_looks_like_product_document_returns_true_for_detected_inventory_sheet():
    datos = {
        "filas_por_hoja": {
            "ARTICULOS": [
                {"Articulo": "Harina premium", "PVP": 42.9, "Existencia": 50},
            ]
        },
        "sheet_usada": "ARTICULOS",
    }

    assert looks_like_product_document(
        datos,
        sheet_name="ARTICULOS",
        detection_config={
            "summary_names": ["total", "subtotal"],
            "name_keywords": ["articulo"],
            "price_keywords": ["pvp"],
            "price_reject_keywords": ["total"],
            "cost_keywords": ["costo"],
            "sku_keywords": ["sku"],
            "category_keywords": ["categoria"],
            "description_keywords": ["descripcion"],
            "explicit_stock_keywords": ["existencia"],
            "ambiguous_stock_keywords": ["cantidad"],
            "operational_keywords": ["venta"],
            "sheet_hint_keywords": ["articulos"],
        },
    )


def test_save_product_candidates_skips_existing_products_and_forwards_category(db, monkeypatch):
    tenant = Tenant(id=uuid4(), name="Import Tenant", slug=f"import-{uuid4().hex[:8]}")
    db.add(tenant)
    db.flush()

    existing = Product(
        tenant_id=tenant.id,
        name="Tapados",
        price=0.5,
        stock=0,
        unit="unit",
        sku="PRO-0001",
        active=True,
    )
    db.add(existing)
    db.flush()

    resolver_calls: list[tuple[object, str]] = []

    def fake_resolve_category_id(_db, tenant_id, category_name):
        resolver_calls.append((tenant_id, category_name))
        return None

    monkeypatch.setattr(product_import_service, "_resolve_category_id", fake_resolve_category_id)
    monkeypatch.setattr(product_import_service, "_generate_next_sku", lambda *_args: "PAN-0002")

    result = save_product_candidates(
        db,
        tenant.id,
        [
            ProductCandidate(
                row_index=0,
                name="Tapados",
                price=0.13,
                stock=0,
                unit="unit",
                category_name="Panaderia",
            ),
            ProductCandidate(
                row_index=1,
                name="Empanadas",
                price=0.2,
                stock=0,
                unit="unit",
                category_name="Panaderia",
            ),
        ],
    )
    db.commit()

    assert result["created"] == 1
    assert result["updated"] == 1
    assert result["skipped_existing"] == 0

    products = (
        db.query(Product).filter(Product.tenant_id == tenant.id).order_by(Product.name.asc()).all()
    )
    assert [product.name for product in products] == ["Empanadas", "Tapados"]
    assert products[0].sku == "PAN-0002"
    assert len(resolver_calls) == 1
    assert str(resolver_calls[0][0]) == str(tenant.id)
    assert resolver_calls[0][1] == "Panaderia"
