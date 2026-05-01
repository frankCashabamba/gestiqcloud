"""Tests para parametrización de `<ambiente>` SRI Ecuador.

Cubre:
- ``_sri_ambiente_code`` → mapping SRISettings.environment → "1" | "2"
- ``generate_clave_acceso`` → dígito 23 = ambiente
- ``generate_sri_xml`` → emite `<ambiente>` y `<claveAcceso>` con el mismo código

NOTA: estos tests no se ejecutan aquí; sólo se escriben.
"""

from __future__ import annotations

import os
from datetime import date

os.environ.setdefault("TEST_MINIMAL", "1")

import pytest
from lxml import etree

from app.workers.einvoicing_tasks import (
    _sri_ambiente_code,
    generate_clave_acceso,
    generate_sri_xml,
)


# ---------------------------------------------------------------------------
# _sri_ambiente_code
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "env,expected",
    [
        ("PRODUCTION", "2"),
        ("production", "2"),
        ("Production", "2"),
        ("  PRODUCTION  ", "2"),
        ("STAGING", "1"),
        ("staging", "1"),
        ("SANDBOX", "1"),
        ("anything-else", "1"),
        ("", "1"),
        (None, "1"),
    ],
)
def test_sri_ambiente_code_mapping(env, expected):
    assert _sri_ambiente_code(env) == expected


# ---------------------------------------------------------------------------
# Fixtures de invoice_data mínimo
# ---------------------------------------------------------------------------


def _invoice_data():
    return {
        "numero": "001-001-000000123",
        "fecha": date(2025, 6, 15),
        "subtotal": 100.0,
        "impuesto": 12.0,
        "total": 112.0,
        "tax_rate": 12,
        "empresa": {
            "nombre": "ACME S.A.",
            "ruc": "1790012345001",
            "direccion": "Av. Siempre Viva 123",
        },
        "cliente": {
            "nombre": "Cliente Demo",
            "ruc": "1712345678001",
            "email": "demo@example.com",
        },
        "lines": [
            {
                "cantidad": 1,
                "precio_unitario": 100.0,
                "total": 100.0,
                "descripcion": "Servicio",
                "sku": "SVC-001",
            }
        ],
    }


# ---------------------------------------------------------------------------
# generate_clave_acceso
# ---------------------------------------------------------------------------


def test_clave_acceso_length_is_49_for_both_ambientes():
    data = _invoice_data()
    for amb in ("1", "2"):
        clave = generate_clave_acceso(data, ambiente=amb)
        assert len(clave) == 49, clave


def test_clave_acceso_embeds_ambiente_at_position_23():
    """Posición 0-indexed 23 = dígito de ambiente.

    Layout: 8 (DDMMAAAA) + 2 (tipo) + 13 (RUC) = 23 → siguiente dígito = ambiente.
    """
    data = _invoice_data()
    clave_pruebas = generate_clave_acceso(data, ambiente="1")
    clave_prod = generate_clave_acceso(data, ambiente="2")
    assert clave_pruebas[23] == "1"
    assert clave_prod[23] == "2"
    # Resto de la clave (excepto verificador) idéntico salvo posición 23
    assert clave_pruebas[:23] == clave_prod[:23]
    assert clave_pruebas[24:48] == clave_prod[24:48]


def test_clave_acceso_default_is_pruebas():
    clave = generate_clave_acceso(_invoice_data())
    assert clave[23] == "1"


# ---------------------------------------------------------------------------
# generate_sri_xml
# ---------------------------------------------------------------------------


def _ambiente_in_xml(xml: str) -> str:
    root = etree.fromstring(xml.encode("utf-8"))
    el = root.find(".//infoTributaria/ambiente")
    assert el is not None
    return el.text or ""


def _clave_in_xml(xml: str) -> str:
    root = etree.fromstring(xml.encode("utf-8"))
    el = root.find(".//infoTributaria/claveAcceso")
    assert el is not None
    return el.text or ""


def test_generate_sri_xml_uses_ambiente_pruebas():
    xml = generate_sri_xml(_invoice_data(), ambiente="1")
    assert _ambiente_in_xml(xml) == "1"
    assert _clave_in_xml(xml)[23] == "1"


def test_generate_sri_xml_uses_ambiente_produccion():
    xml = generate_sri_xml(_invoice_data(), ambiente="2")
    assert _ambiente_in_xml(xml) == "2"
    assert _clave_in_xml(xml)[23] == "2"


def test_generate_sri_xml_default_ambiente_is_pruebas():
    xml = generate_sri_xml(_invoice_data())
    assert _ambiente_in_xml(xml) == "1"


# ---------------------------------------------------------------------------
# Integración: el código resuelto desde SRISettings.environment debe propagarse
# coherentemente a XML y clave de acceso.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "environment,expected_code",
    [("PRODUCTION", "2"), ("STAGING", "1"), (None, "1")],
)
def test_settings_environment_flows_into_xml_and_clave(environment, expected_code):
    code = _sri_ambiente_code(environment)
    assert code == expected_code

    data = _invoice_data()
    xml = generate_sri_xml(data, ambiente=code)
    clave = generate_clave_acceso(data, ambiente=code)

    assert _ambiente_in_xml(xml) == expected_code
    assert _clave_in_xml(xml) == clave
    assert clave[23] == expected_code
