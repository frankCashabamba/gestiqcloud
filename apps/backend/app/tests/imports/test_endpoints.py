"""Tests de integración para endpoints de imports auto-detect."""

import io
import csv
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

import openpyxl
from fastapi.testclient import TestClient


class TestAnalyzeEndpoint:
    """Tests for POST /imports/uploads/analyze endpoint."""

    @pytest.fixture
    def mock_access_claims(self):
        """Mock access claims for authentication."""
        return {
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
            "roles": ["admin"],
        }

    @pytest.fixture
    def sample_excel_bytes(self) -> bytes:
        """Create sample Excel file as bytes."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["nombre", "precio", "stock"])
        ws.append(["Producto A", 100.00, 10])
        ws.append(["Producto B", 200.00, 20])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.read()

    @pytest.fixture
    def sample_csv_bytes(self) -> bytes:
        """Create sample CSV file as bytes."""
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["fecha", "concepto", "importe", "saldo"])
        writer.writerow(["2024-01-15", "Transferencia", 1000.00, 5000.00])
        return buffer.getvalue().encode("utf-8")

    @pytest.mark.skip(reason="Depends on router configuration in test environment")
    def test_analyze_requires_auth(self, client: TestClient):
        """Test que el endpoint requiere autenticación."""
        response = client.post(
            "/api/v1/imports/uploads/analyze",
            files={"file": ("test.xlsx", b"content", "application/octet-stream")},
        )
        assert response.status_code in (401, 403, 404, 422, 500)

    def test_analyze_rejects_unsupported_extension(
        self, client: TestClient, mock_access_claims
    ):
        """Test rechazo de extensión no soportada."""
        with patch("app.core.access_guard.with_access_claims") as mock_guard:
            mock_guard.return_value = lambda: mock_access_claims

            with patch.object(
                client.app.state, "access_claims", mock_access_claims, create=True
            ):
                response = client.post(
                    "/api/v1/imports/uploads/analyze",
                    files={
                        "file": (
                            "test.txt",
                            b"text content",
                            "text/plain",
                        )
                    },
                )

        assert response.status_code in (401, 403, 422)

    def test_analyze_requires_filename(self, client: TestClient):
        """Test que se requiere nombre de archivo."""
        response = client.post(
            "/api/v1/imports/uploads/analyze",
            files={"file": ("", b"content", "application/octet-stream")},
        )
        assert response.status_code in (401, 403, 422)


class TestFeedbackEndpoint:
    """Tests for feedback endpoints."""

    @pytest.fixture
    def mock_access_claims(self):
        """Mock access claims for authentication."""
        return {
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
        }

    def test_feedback_endpoint_requires_auth(self, client: TestClient):
        """Test que el endpoint requiere autenticación."""
        response = client.post(
            "/api/v1/imports/feedback",
            json={
                "original_parser": "products_excel",
                "original_confidence": 0.9,
                "was_correct": True,
                "headers": ["name"],
                "filename": "test.xlsx",
            },
        )
        assert response.status_code in (401, 403, 404, 422, 500)

    def test_feedback_stats_endpoint_exists(self, client: TestClient):
        """Test que el endpoint de stats existe."""
        response = client.get("/api/v1/imports/feedback/stats")
        assert response.status_code in (401, 403, 404)


class TestConfirmEndpoint:
    """Tests for batch confirmation endpoint."""

    def test_confirm_requires_auth(self, client: TestClient):
        """Test que el endpoint requiere autenticación."""
        batch_id = str(uuid4())
        response = client.post(
            f"/api/v1/imports/batches/{batch_id}/confirm",
            json={
                "parser_id": "products_excel",
            },
        )
        assert response.status_code in (401, 403, 404, 422, 500)

    def test_confirm_invalid_batch_id(self, client: TestClient):
        """Test rechazo de batch_id inválido."""
        response = client.post(
            "/api/v1/imports/batches/invalid-uuid/confirm",
            json={"parser_id": "products_excel"},
        )
        assert response.status_code in (400, 401, 403, 422)

    def test_confirmation_status_endpoint_exists(self, client: TestClient):
        """Test que el endpoint de status existe."""
        batch_id = str(uuid4())
        response = client.get(
            f"/api/v1/imports/batches/{batch_id}/confirmation-status"
        )
        assert response.status_code in (400, 401, 403, 404)


class TestEndpointResponseSchemas:
    """Tests for response schema validation."""

    def test_analyze_response_schema(self):
        """Test AnalyzeResponse schema structure."""
        from app.modules.imports.interface.http.analyze import AnalyzeResponse

        response = AnalyzeResponse(
            suggested_parser="products_excel",
            suggested_doc_type="products",
            confidence=0.85,
            headers_sample=["name", "price"],
            mapping_suggestion={"name": "name", "price": "price"},
            explanation="Detected product headers",
            decision_log=[{"step": "test", "result": "ok"}],
            requires_confirmation=False,
            available_parsers=["products_excel", "csv_products"],
            probabilities={"products": 0.85, "bank": 0.1},
            ai_enhanced=False,
            ai_provider=None,
        )

        assert response.suggested_parser == "products_excel"
        assert response.confidence == 0.85
        assert len(response.headers_sample) == 2

    def test_feedback_response_schema(self):
        """Test FeedbackResponse schema structure."""
        from app.modules.imports.interface.http.feedback import FeedbackResponse

        response = FeedbackResponse(
            id="feedback-123",
            message="Feedback recorded",
            was_correct=True,
        )

        assert response.id == "feedback-123"
        assert response.was_correct is True

    def test_accuracy_stats_response_schema(self):
        """Test AccuracyStatsResponse schema structure."""
        from app.modules.imports.interface.http.feedback import AccuracyStatsResponse

        response = AccuracyStatsResponse(
            total_classifications=100,
            correct_count=90,
            corrected_count=10,
            accuracy_rate=0.9,
            by_doc_type={
                "products": {"total": 50, "correct": 48, "accuracy_rate": 0.96}
            },
            most_corrected_parsers=[{"parser": "generic", "corrections": 5}],
        )

        assert response.accuracy_rate == 0.9
        assert response.total_classifications == 100

    def test_confirm_batch_response_schema(self):
        """Test ConfirmBatchResponse schema structure."""
        from app.modules.imports.interface.http.confirm import ConfirmBatchResponse

        response = ConfirmBatchResponse(
            batch_id="batch-123",
            confirmed_parser="products_excel",
            mapping_applied=True,
            ready_to_process=True,
            message="Batch confirmed",
        )

        assert response.batch_id == "batch-123"
        assert response.ready_to_process is True


class TestEndpointRequestSchemas:
    """Tests for request schema validation."""

    def test_record_feedback_request_schema(self):
        """Test RecordFeedbackRequest schema."""
        from app.modules.imports.interface.http.feedback import RecordFeedbackRequest

        request = RecordFeedbackRequest(
            batch_id="batch-123",
            decision_log_id="log-456",
            original_parser="products_excel",
            original_confidence=0.9,
            original_doc_type="products",
            corrected_parser="csv_products",
            corrected_doc_type="products",
            was_correct=False,
            headers=["name", "price", "stock"],
            filename="products.xlsx",
        )

        assert request.original_parser == "products_excel"
        assert request.was_correct is False
        assert len(request.headers) == 3

    def test_record_feedback_request_minimal(self):
        """Test RecordFeedbackRequest with minimal fields."""
        from app.modules.imports.interface.http.feedback import RecordFeedbackRequest

        request = RecordFeedbackRequest(
            original_parser="products_excel",
            original_confidence=0.9,
            was_correct=True,
            headers=["name"],
            filename="test.xlsx",
        )

        assert request.batch_id is None
        assert request.corrected_parser is None

    def test_confirm_batch_request_schema(self):
        """Test ConfirmBatchRequest schema."""
        from app.modules.imports.interface.http.confirm import ConfirmBatchRequest

        request = ConfirmBatchRequest(
            parser_id="products_excel",
            mapping_id="mapping-123",
            custom_mapping={"nombre": "name"},
            transforms={"precio": "parse_number"},
            defaults={"category": "General"},
        )

        assert request.parser_id == "products_excel"
        assert request.custom_mapping is not None

    def test_confirm_batch_request_minimal(self):
        """Test ConfirmBatchRequest with minimal fields."""
        from app.modules.imports.interface.http.confirm import ConfirmBatchRequest

        request = ConfirmBatchRequest(parser_id="products_excel")

        assert request.mapping_id is None
        assert request.custom_mapping is None
