import pytest
from pydantic import ValidationError

from app.modules.suppliers.interface.http.schemas import SupplierCreate, SupplierUpdate


def test_supplier_update_accepts_partial_payload():
    payload = SupplierUpdate(payment_days=30)

    assert payload.model_dump(exclude_unset=True) == {"payment_days": 30}


def test_supplier_iban_is_normalized_and_validated():
    payload = SupplierCreate(
        name="Proveedor",
        iban="es91 2100 0418 4502 0005 1332",
        iban_confirmation="ES9121000418450200051332",
    )

    assert payload.iban == "ES9121000418450200051332"
    assert payload.iban_confirmation == "ES9121000418450200051332"


def test_supplier_iban_rejects_invalid_checksum():
    with pytest.raises(ValidationError):
        SupplierCreate(
            name="Proveedor",
            iban="ES9121000418450200051333",
            iban_confirmation="ES9121000418450200051333",
        )
