"""Test end-to-end del pipeline con test redis."""
from __future__ import annotations

import pytest
import os
from uuid import uuid4
from unittest.mock import MagicMock, patch
from app.modules.imports.domain.pipeline import enqueue_item_pipeline, RUNNER_MODE


@pytest.mark.skipif(RUNNER_MODE != "inline", reason="Requires inline mode for tests")
def test_pipeline_inline_mode():
    os.environ["IMPORTS_RUNNER_MODE"] = "inline"
    
    item_id = uuid4()
    tenant_id = uuid4()
    batch_id = uuid4()
    
    with patch("app.modules.imports.domain.pipeline.session_scope") as mock_session:
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        
        mock_item = MagicMock()
        mock_item.id = item_id
        mock_item.file_data = b"%PDF-1.4 test"
        mock_item.filename = "test.pdf"
        mock_item.mime_type = "application/pdf"
        mock_item.ocr_result = {"documentos": [{"texto": "test"}]}
        mock_item.doc_type = "factura"
        mock_item.extracted_data = {"numero": "001"}
        mock_item.metadata = {}
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_item
        mock_db.execute = MagicMock()
        
        with patch("app.modules.imports.application.tasks.task_preprocess.preprocess_item"):
            with patch("app.modules.imports.application.tasks.task_ocr.ocr_item"):
                with patch("app.modules.imports.application.tasks.task_classify.classify_item"):
                    result = enqueue_item_pipeline(item_id, tenant_id, batch_id)
                    
                    assert result == "inline"


def test_pipeline_idempotence():
    item_id = uuid4()
    tenant_id = uuid4()
    batch_id = uuid4()
    
    result1 = enqueue_item_pipeline(item_id, tenant_id, batch_id)
    result2 = enqueue_item_pipeline(item_id, tenant_id, batch_id)
    
    assert result1 == result2
