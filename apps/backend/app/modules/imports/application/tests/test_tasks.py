"""Unit tests para tasks con mock."""

from __future__ import annotations

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from app.modules.imports.application.tasks.task_preprocess import preprocess_item
from app.modules.imports.application.tasks.task_classify import _classify_document


def test_preprocess_validates_file_size():
    item_id = str(uuid4())
    tenant_id = str(uuid4())
    batch_id = str(uuid4())

    with patch(
        "app.modules.imports.application.tasks.task_preprocess.session_scope"
    ) as mock_session:
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db

        mock_item = MagicMock()
        mock_item.id = uuid4()
        mock_item.file_data = b""
        mock_item.mime_type = "application/pdf"
        mock_item.metadata = {}

        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        with pytest.raises(ValueError, match="Empty file"):
            preprocess_item(None, item_id, tenant_id, batch_id)


def test_classify_document_returns_factura():
    ocr_result = {"documentos": [{"texto": "FACTURA NIF B12345678 IVA 21%"}]}

    result = _classify_document(ocr_result)  # noqa: F841
    assert result == "factura"


def test_classify_document_returns_desconocido():
    ocr_result = {"documentos": []}

    result = _classify_document(ocr_result)  # noqa: F841
    assert result == "desconocido"


def test_classify_document_banco():
    ocr_result = {
        "documentos": [{"texto": "EXTRACTO BANCARIO IBAN ES12 3456 SALDO 1000"}]
    }

    result = _classify_document(ocr_result)  # noqa: F841
    assert result == "banco"
