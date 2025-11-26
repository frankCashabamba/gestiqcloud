"""
Parser genérico para cualquier archivo Excel.
Auto-detecta estructura y normaliza datos sin importar el banco o formato.
"""

from datetime import datetime
from typing import Any

import openpyxl


def parse_excel_generic(file_path: str, sheet_name: str | None = None) -> dict[str, Any]:
    """
    Parser universal para Excel de cualquier formato.

    Detecta automáticamente:
    - Headers (busca fila con más celdas llenas)
    - Tipo de datos (productos, banco, facturas)
    - Columnas relevantes (flexible, múltiples alias)

    Args:
        file_path: Ruta al archivo Excel
        sheet_name: Nombre de hoja (default: primera hoja o sheet con más datos)

    Returns:
        Dict con rows normalizadas y metadata
    """
    wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)

    # Seleccionar sheet con más datos si no se especifica
    if sheet_name:
        ws = wb[sheet_name]
    else:
        # Buscar sheet con más filas
        best_sheet = None
        max_rows = 0
        for sheet in wb.worksheets:
            rows_count = sum(1 for _ in sheet.iter_rows())
            if rows_count > max_rows:
                max_rows = rows_count
                best_sheet = sheet
        ws = best_sheet or wb.active

    rows = list(ws.iter_rows(values_only=True, max_row=10000))
    if not rows:
        return {"rows": [], "headers": [], "metadata": {}, "detected_type": "empty"}

    # Detectar fila de headers (la que tiene más celdas no vacías en primeras 20 filas)
    header_row_idx = 0
    max_filled = 0
    for idx, row in enumerate(rows[:20]):
        filled = sum(1 for cell in row if cell is not None and str(cell).strip())
        if filled > max_filled:
            max_filled = filled
            header_row_idx = idx

    header = rows[header_row_idx]

    # Normalizar headers
    normalized_headers = []
    for cell in header:
        if cell is None or str(cell).strip() == "":
            normalized_headers.append(None)
        else:
            normalized_headers.append(str(cell).strip())

    # Extraer datos
    data_rows = []
    for row_idx, row in enumerate(rows[header_row_idx + 1 :], start=header_row_idx + 2):
        if not row or all(cell is None or str(cell).strip() == "" for cell in row):
            continue

        row_dict = {}
        for idx, (header_name, cell_value) in enumerate(zip(normalized_headers, row, strict=False)):
            if header_name is None:
                header_name = f"_col_{idx}"

            # Normalizar valores
            if cell_value is None:
                row_dict[header_name] = None
            elif isinstance(cell_value, (int, float)):
                row_dict[header_name] = cell_value
            elif isinstance(cell_value, datetime):
                row_dict[header_name] = cell_value.date().isoformat()
            else:
                row_dict[header_name] = str(cell_value).strip()

        # Saltar filas completamente vacías
        if all(v is None or v == "" for v in row_dict.values()):
            continue

        row_dict["_row"] = row_idx
        row_dict["_imported_at"] = datetime.utcnow().isoformat()
        data_rows.append(row_dict)

    # Detectar tipo de documento por keywords en headers
    headers_str = " ".join([str(h or "").upper() for h in normalized_headers])

    detected_type = "generic"
    if any(kw in headers_str for kw in ["PRODUCTO", "NOMBRE", "PRECIO", "STOCK", "SKU", "CODIGO"]):
        detected_type = "products"
    elif any(kw in headers_str for kw in ["FECHA", "IMPORTE", "SALDO", "BANCO", "IBAN", "CUENTA"]):
        detected_type = "bank"
    elif any(
        kw in headers_str
        for kw in ["FACTURA", "INVOICE", "VENDOR", "SUPPLIER", "CLIENT", "IVA", "TAX"]
    ):
        detected_type = "invoices"

    metadata = {
        "sheet_name": ws.title,
        "header_row": header_row_idx + 1,
        "total_rows": len(data_rows),
        "detected_type": detected_type,
        "file_path": file_path,
    }

    return {
        "rows": data_rows,
        "headers": [h for h in normalized_headers if h is not None],
        "metadata": metadata,
        "detected_type": detected_type,
    }
