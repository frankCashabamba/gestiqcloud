from decimal import Decimal

from app.modules.importador.daily_log_service import parse_registro_rows


def test_parse_registro_rows_supports_normalized_excel_dict_rows():
    datos_extraidos = {
        "filas_por_hoja": {
            "REGISTRO": [
                {
                    "producto": "PAN",
                    "cantidad": None,
                    "precio_unitario_venta": None,
                    "sobrante_diario": None,
                    "venta___diaria": None,
                    "total": 108.39,
                    "_sheet": "REGISTRO",
                },
                {
                    "producto": "tapados",
                    "cantidad": 292,
                    "precio_unitario_venta": 0.13,
                    "sobrante_diario": 52,
                    "venta___diaria": 240,
                    "total": 31.2,
                    "_sheet": "REGISTRO",
                },
                {
                    "producto": "empanadas",
                    "cantidad": 72,
                    "precio_unitario_venta": 0.2,
                    "sobrante_diario": 0,
                    "venta___diaria": 72,
                    "total": 14.4,
                    "_sheet": "REGISTRO",
                },
            ]
        }
    }

    rows = parse_registro_rows(datos_extraidos)

    assert rows == [
        {
            "product_name": "tapados",
            "qty_produced": Decimal("292.0000"),
            "unit_price": Decimal("0.1300"),
            "qty_sold": Decimal("240.0000"),
        },
        {
            "product_name": "empanadas",
            "qty_produced": Decimal("72.0000"),
            "unit_price": Decimal("0.2000"),
            "qty_sold": Decimal("72.0000"),
        },
    ]


def test_parse_registro_rows_supports_generic_dict_headers_without_aliases():
    datos_extraidos = {
        "filas_por_hoja": {
            "REGISTRO": [
                {"col_a": "PAN", "col_b": None, "col_c": None, "col_d": 108.39, "col_e": None},
                {"col_a": "tapados", "col_b": 292, "col_c": 0.13, "col_d": 31.2, "col_e": 240},
                {"col_a": "empanadas", "col_b": 72, "col_c": 0.2, "col_d": 14.4, "col_e": 72},
            ]
        }
    }

    rows = parse_registro_rows(datos_extraidos)

    assert rows == [
        {
            "product_name": "tapados",
            "qty_produced": Decimal("292.0000"),
            "unit_price": Decimal("0.1300"),
            "qty_sold": Decimal("240.0000"),
        },
        {
            "product_name": "empanadas",
            "qty_produced": Decimal("72.0000"),
            "unit_price": Decimal("0.2000"),
            "qty_sold": Decimal("72.0000"),
        },
    ]


def test_parse_registro_rows_supports_generic_legacy_matrix_rows():
    datos_extraidos = {
        "filas": [
            ["A", "B", "C", "D", "E"],
            ["PAN", "", "", "108,39", ""],
            ["tapados", "292", "0,13", "31,20", "240"],
            ["empanadas", "72", "0,20", "14,40", "72"],
        ]
    }

    rows = parse_registro_rows(datos_extraidos)

    assert rows == [
        {
            "product_name": "tapados",
            "qty_produced": Decimal("292.0000"),
            "unit_price": Decimal("0.1300"),
            "qty_sold": Decimal("240.0000"),
        },
        {
            "product_name": "empanadas",
            "qty_produced": Decimal("72.0000"),
            "unit_price": Decimal("0.2000"),
            "qty_sold": Decimal("72.0000"),
        },
    ]
