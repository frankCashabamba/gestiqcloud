"""
Tests para el importador de productos desde Excel/CSV
"""
import tempfile
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.core.producto import Producto, Base
from app.models.inventory.stock import StockItem
from app.services.products_importer import ProductsImporter


@pytest.fixture
def db_session():
    """Crear sesión de BD en memoria para tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_excel_file():
    """Crear archivo Excel de ejemplo."""
    data = {
        "PRODUCTO": ["tapados", "pan dulce", "empanadas queso", "Total"],
        "CANTIDAD": [196, 10, 30, "=SUM(B1:B3)"],
        "PRECIO": [0.15, 0.15, 0.20, None],
        "CATEGORIA": ["PAN", "PAN", "SALADOS", None],
    }
    df = pd.DataFrame(data)
    
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        df.to_excel(tmp.name, index=False, sheet_name="Productos")
        return tmp.name


def test_import_basic(db_session: Session, sample_excel_file: str):
    """Test importación básica de productos."""
    importer = ProductsImporter(
        db=db_session,
        tenant_id="test-tenant-123",
    )
    
    stats = importer.import_from_excel(
        file_path=sample_excel_file,
        sheet_name="Productos",
    )
    
    # Verificar estadísticas
    assert stats["products_created"] == 3  # Excluye fila "Total"
    assert stats["stock_initialized"] == 3
    assert len(stats["errors"]) == 0
    
    # Verificar productos creados
    products = db_session.query(Producto).all()
    assert len(products) == 3
    
    # Verificar primer producto
    tapados = db_session.query(Producto).filter_by(nombre="tapados").first()
    assert tapados is not None
    assert tapados.precio_venta == Decimal("0.15")
    assert tapados.categoria == "PAN"
    
    # Verificar stock
    stock = db_session.query(StockItem).filter_by(product_id=tapados.id).first()
    assert stock is not None
    assert stock.qty_on_hand == Decimal("196")
    
    # Limpiar
    Path(sample_excel_file).unlink()


def test_import_skip_duplicates(db_session: Session, sample_excel_file: str):
    """Test que no duplica productos existentes."""
    # Primera importación
    importer1 = ProductsImporter(db=db_session, tenant_id="test-tenant")
    stats1 = importer1.import_from_excel(sample_excel_file, "Productos")
    
    assert stats1["products_created"] == 3
    
    # Segunda importación (sin update_existing)
    importer2 = ProductsImporter(db=db_session, tenant_id="test-tenant")
    stats2 = importer2.import_from_excel(
        sample_excel_file,
        "Productos",
        update_existing=False,
    )
    
    assert stats2["products_created"] == 0
    assert stats2["products_skipped"] == 3
    
    # Verificar que solo hay 3 productos
    total_products = db_session.query(Producto).count()
    assert total_products == 3
    
    Path(sample_excel_file).unlink()


def test_import_update_existing(db_session: Session, sample_excel_file: str):
    """Test actualización de productos existentes."""
    # Crear producto inicial
    existing = Producto(
        tenant_id="test-tenant",
        nombre="tapados",
        precio_venta=Decimal("0.10"),  # Precio antiguo
    )
    db_session.add(existing)
    db_session.commit()
    
    # Importar con actualización
    importer = ProductsImporter(db=db_session, tenant_id="test-tenant")
    stats = importer.import_from_excel(
        sample_excel_file,
        "Productos",
        update_existing=True,
    )
    
    assert stats["products_updated"] == 1
    assert stats["products_created"] == 2  # Los otros 2
    
    # Verificar que se actualizó el precio
    updated = db_session.query(Producto).filter_by(nombre="tapados").first()
    assert updated.precio_venta == Decimal("0.15")
    
    Path(sample_excel_file).unlink()


def test_column_detection():
    """Test detección automática de columnas."""
    # Archivo con nombres alternativos
    data = {
        "NAME": ["Producto 1"],
        "QTY": [50],
        "PRICE": [1.50],
    }
    df = pd.DataFrame(data)
    
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        df.to_excel(tmp.name, index=False)
        tmp_path = tmp.name
    
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    importer = ProductsImporter(db=session, tenant_id="test")
    stats = importer.import_from_excel(tmp_path)
    
    assert stats["products_created"] == 1
    
    product = session.query(Producto).first()
    assert product.nombre == "Producto 1"
    
    stock = session.query(StockItem).first()
    assert stock.qty_on_hand == Decimal("50")
    
    session.close()
    Path(tmp_path).unlink()


def test_normalize_number():
    """Test normalización de números."""
    from app.services.products_importer import ProductsImporter
    
    assert ProductsImporter._normalize_number("123.45") == Decimal("123.45")
    assert ProductsImporter._normalize_number("123,45") == Decimal("123.45")
    assert ProductsImporter._normalize_number(196) == Decimal("196")
    assert ProductsImporter._normalize_number("=SUM(A1:A10)") is None  # Fórmula
    assert ProductsImporter._normalize_number(None) is None
    assert ProductsImporter._normalize_number("") is None


def test_normalize_text():
    """Test normalización de texto."""
    from app.services.products_importer import ProductsImporter
    
    assert ProductsImporter._normalize_text("  Pan  ") == "Pan"
    assert ProductsImporter._normalize_text(None) is None
    assert ProductsImporter._normalize_text("") is None
    assert ProductsImporter._normalize_text(123) == "123"


def test_real_client_file():
    """
    Test con archivo real del cliente (22-10-20251.xlsx).
    
    Este test requiere el archivo real en el directorio raíz.
    """
    client_file = Path(__file__).parent.parent.parent.parent / "22-10-20251.xlsx"
    
    if not client_file.exists():
        pytest.skip(f"Archivo cliente no encontrado: {client_file}")
    
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    importer = ProductsImporter(db=session, tenant_id="panaderia-test")
    stats = importer.import_from_excel(
        str(client_file),
        sheet_name="REGISTRO",
    )
    
    # Verificar resultados
    assert stats["products_created"] > 30  # Al menos 30 productos
    assert stats["stock_initialized"] > 30
    assert len(stats["errors"]) == 0
    
    # Verificar un producto específico
    tapados = session.query(Producto).filter_by(nombre="tapados").first()
    if tapados:
        assert tapados.precio_venta == Decimal("0.15")
        
        stock = session.query(StockItem).filter_by(product_id=tapados.id).first()
        assert stock.qty_on_hand == Decimal("196")
    
    session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
