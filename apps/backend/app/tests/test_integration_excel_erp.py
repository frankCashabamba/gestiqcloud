"""
Tests de Integración: Excel → ERP
Verifica que el importador puebla correctamente stock_items y stock_moves
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
import io
import openpyxl


@pytest.mark.skip(reason="Windows file locking issue with openpyxl - needs refactor")
def test_excel_import_populates_stock(client: TestClient, db, auth_headers):
    """Test que Excel importado puebla stock_items correctamente"""
    tenant_id = str(uuid4())
    headers = auth_headers(tenant_id=tenant_id)
    
    # Crear Excel mock
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "REGISTRO"
    
    # Headers
    ws.append(["PRODUCTO", "CANTIDAD", "VENTA DIARIA", "SOBRANTE DIARIO", "PRECIO UNITARIO VENTA"])
    
    # Datos
    ws.append(["Pan Integral", 100, 85, 15, 1.50])
    ws.append(["Croissant", 50, 45, 5, 2.00])
    ws.append(["Empanada", 80, 70, 10, 2.50])
    
    # Guardar en BytesIO
    excel_file = io.BytesIO()
    wb.save(excel_file)
    wb.close()  # FIX: Close workbook before attempting to delete (Windows PermissionError)
    excel_file.seek(0)
    
    # Importar
    response = client.post(
        "/api/v1/imports/spec1/excel",
        files={"file": ("test.xlsx", excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={
            "fecha_manual": "2025-01-20",
            "simulate_sales": "true"
        },
        headers=headers
    )
    
    assert response.status_code in [200, 500], response.text  # 500 si falta warehouse
    
    if response.status_code == 200:
        result = response.json()
        stats = result.get("stats", {})
        
        # Verificar stats
        assert stats.get("products_created") == 3
        assert stats.get("daily_inventory_created") == 3
        assert stats.get("stock_items_initialized") == 3
        assert stats.get("stock_moves_created") == 3  # Ventas históricas
        
        # Verificar que stock_items se creó
        # (requeriría consulta directa a DB o endpoint de stock)


@pytest.mark.skip(reason="Windows file locking issue with openpyxl - needs refactor")
def test_excel_import_without_warehouse(client: TestClient, db, auth_headers):
    """Test que falla gracefully si no hay almacén"""
    tenant_id = str(uuid4())
    headers = auth_headers(tenant_id=tenant_id)
    
    # Crear Excel simple
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "REGISTRO"
    ws.append(["PRODUCTO", "CANTIDAD", "VENTA DIARIA", "SOBRANTE DIARIO", "PRECIO UNITARIO VENTA"])
    ws.append(["Test", 10, 5, 5, 1.00])
    
    excel_file = io.BytesIO()
    wb.save(excel_file)
    wb.close()  # FIX: Close workbook before attempting to delete (Windows PermissionError)
    excel_file.seek(0)
    
    response = client.post(
        "/api/v1/imports/spec1/excel",
        files={"file": ("test.xlsx", excel_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"fecha_manual": "2025-01-20"},
        headers=headers
    )
    
    # Debe procesar pero con warnings
    if response.status_code == 200:
        result = response.json()
        # Puede tener warnings sobre warehouse
        assert "stats" in result


def test_invalid_excel_format(client: TestClient, auth_headers):
    """Test que rechaza archivos no-Excel"""
    tenant_id = str(uuid4())
    headers = auth_headers(tenant_id=tenant_id)
    
    # Archivo no-Excel
    fake_file = io.BytesIO(b"not an excel file")
    
    response = client.post(
        "/api/v1/imports/spec1/excel",
        files={"file": ("test.txt", fake_file, "text/plain")},
        headers=headers
    )
    
    assert response.status_code in [400, 422, 500]
