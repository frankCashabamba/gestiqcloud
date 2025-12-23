"""Tests for FeedbackService."""

import json
import pytest
from datetime import datetime
from pathlib import Path

from app.modules.imports.services.feedback_service import (
    FeedbackService,
    FeedbackEntry,
    feedback_service,
)


class TestFeedbackService:
    """Test FeedbackService functionality."""

    @pytest.fixture
    def service(self, tmp_path) -> FeedbackService:
        """Create FeedbackService with temp storage."""
        return FeedbackService(storage_path=str(tmp_path / "feedback"))

    def test_record_correct_feedback(self, service):
        """Test registro de clasificación correcta."""
        entry = service.record_feedback(
            tenant_id="tenant-1",
            original_parser="products_excel",
            original_confidence=0.9,
            original_doc_type="products",
            corrected_parser=None,
            corrected_doc_type=None,
            was_correct=True,
            headers=["nombre", "precio", "stock"],
            filename="products.xlsx",
        )

        assert entry.id is not None
        assert entry.was_correct is True
        assert entry.original_parser == "products_excel"
        assert entry.corrected_parser is None
        assert entry.tenant_id == "tenant-1"
        assert entry.file_extension == "xlsx"

    def test_record_correction_feedback(self, service):
        """Test registro de corrección."""
        entry = service.record_feedback(
            tenant_id="tenant-1",
            original_parser="generic_csv",
            original_confidence=0.5,
            original_doc_type="unknown",
            corrected_parser="csv_bank",
            corrected_doc_type="bank_transactions",
            was_correct=False,
            headers=["fecha", "importe", "saldo"],
            filename="movements.csv",
        )

        assert entry.was_correct is False
        assert entry.corrected_parser == "csv_bank"
        assert entry.corrected_doc_type == "bank_transactions"
        assert entry.original_parser == "generic_csv"

    def test_record_feedback_with_decision_log_id(self, service):
        """Test registro con decision_log_id."""
        entry = service.record_feedback(
            tenant_id="tenant-1",
            original_parser="products_excel",
            original_confidence=0.8,
            original_doc_type="products",
            corrected_parser=None,
            corrected_doc_type=None,
            was_correct=True,
            headers=["name", "price"],
            filename="data.xlsx",
            decision_log_id="log-123",
        )

        assert entry.decision_log_id == "log-123"

    def test_accuracy_stats_empty(self, service):
        """Test estadísticas con sin datos."""
        stats = service.get_accuracy_stats()

        assert stats["total_classifications"] == 0
        assert stats["correct_count"] == 0
        assert stats["corrected_count"] == 0
        assert stats["accuracy_rate"] == 0.0
        assert stats["by_doc_type"] == {}
        assert stats["most_corrected_parsers"] == []

    def test_accuracy_stats(self, service):
        """Test cálculo de estadísticas."""
        service.record_feedback(
            tenant_id="t1",
            original_parser="products_excel",
            original_confidence=0.9,
            original_doc_type="products",
            corrected_parser=None,
            corrected_doc_type=None,
            was_correct=True,
            headers=["name"],
            filename="f1.xlsx",
        )
        service.record_feedback(
            tenant_id="t1",
            original_parser="products_excel",
            original_confidence=0.85,
            original_doc_type="products",
            corrected_parser=None,
            corrected_doc_type=None,
            was_correct=True,
            headers=["name"],
            filename="f2.xlsx",
        )
        service.record_feedback(
            tenant_id="t1",
            original_parser="generic_csv",
            original_confidence=0.4,
            original_doc_type="products",
            corrected_parser="csv_bank",
            corrected_doc_type="bank",
            was_correct=False,
            headers=["date"],
            filename="f3.csv",
        )

        stats = service.get_accuracy_stats()

        assert stats["total_classifications"] == 3
        assert stats["correct_count"] == 2
        assert stats["corrected_count"] == 1
        assert stats["accuracy_rate"] == pytest.approx(2 / 3)
        assert "products" in stats["by_doc_type"]
        assert stats["by_doc_type"]["products"]["total"] == 3
        assert stats["by_doc_type"]["products"]["correct"] == 2

    def test_accuracy_stats_by_tenant(self, service):
        """Test estadísticas filtradas por tenant."""
        service.record_feedback(
            tenant_id="t1",
            original_parser="p1",
            original_confidence=0.9,
            original_doc_type="products",
            corrected_parser=None,
            corrected_doc_type=None,
            was_correct=True,
            headers=[],
            filename="f1.xlsx",
        )
        service.record_feedback(
            tenant_id="t2",
            original_parser="p1",
            original_confidence=0.9,
            original_doc_type="products",
            corrected_parser=None,
            corrected_doc_type=None,
            was_correct=True,
            headers=[],
            filename="f2.xlsx",
        )

        stats_t1 = service.get_accuracy_stats(tenant_id="t1")
        stats_all = service.get_accuracy_stats()

        assert stats_t1["total_classifications"] == 1
        assert stats_all["total_classifications"] == 2

    def test_most_corrected_parsers(self, service):
        """Test ranking de parsers más corregidos."""
        for i in range(5):
            service.record_feedback(
                tenant_id="t1",
                original_parser="bad_parser",
                original_confidence=0.3,
                original_doc_type="products",
                corrected_parser="good_parser",
                corrected_doc_type="products",
                was_correct=False,
                headers=[],
                filename=f"file{i}.csv",
            )

        for i in range(2):
            service.record_feedback(
                tenant_id="t1",
                original_parser="mediocre_parser",
                original_confidence=0.5,
                original_doc_type="products",
                corrected_parser="good_parser",
                corrected_doc_type="products",
                was_correct=False,
                headers=[],
                filename=f"file_m{i}.csv",
            )

        stats = service.get_accuracy_stats()

        assert len(stats["most_corrected_parsers"]) >= 2
        assert stats["most_corrected_parsers"][0]["parser"] == "bad_parser"
        assert stats["most_corrected_parsers"][0]["corrections"] == 5

    def test_get_training_data_insufficient(self, service):
        """Test que no retorna datos si hay pocos ejemplos."""
        service.record_feedback(
            tenant_id="t1",
            original_parser="p1",
            original_confidence=0.3,
            original_doc_type="products",
            corrected_parser="p2",
            corrected_doc_type="bank",
            was_correct=False,
            headers=["a", "b"],
            filename="f.csv",
        )

        training_data = service.get_training_data(min_entries=50)
        assert training_data == []

    def test_get_training_data(self, service):
        """Test generación de datos de entrenamiento."""
        for i in range(60):
            service.record_feedback(
                tenant_id="t1",
                original_parser="generic",
                original_confidence=0.3,
                original_doc_type="unknown",
                corrected_parser="products_excel",
                corrected_doc_type="products",
                was_correct=False,
                headers=["nombre", "precio", "stock"],
                filename=f"file{i}.xlsx",
            )

        training_data = service.get_training_data(min_entries=50)

        assert len(training_data) >= 50
        assert all(len(item) == 2 for item in training_data)
        headers, doc_type = training_data[0]
        assert isinstance(headers, list)
        assert doc_type == "products"

    def test_export_for_retraining(self, service):
        """Test exportación para reentrenamiento."""
        service.record_feedback(
            tenant_id="t1",
            original_parser="p1",
            original_confidence=0.9,
            original_doc_type="products",
            corrected_parser=None,
            corrected_doc_type=None,
            was_correct=True,
            headers=["name"],
            filename="f.xlsx",
        )

        export = service.export_for_retraining()

        assert "total_entries" in export
        assert "training_samples" in export
        assert "data" in export
        assert "stats" in export
        assert "exported_at" in export
        assert export["total_entries"] == 1

    def test_persistence(self, tmp_path):
        """Test que los datos se persisten y cargan."""
        storage_path = str(tmp_path / "feedback_persist")

        service1 = FeedbackService(storage_path=storage_path)
        service1.record_feedback(
            tenant_id="t1",
            original_parser="p1",
            original_confidence=0.9,
            original_doc_type="products",
            corrected_parser=None,
            corrected_doc_type=None,
            was_correct=True,
            headers=["name"],
            filename="test.xlsx",
        )

        service2 = FeedbackService(storage_path=storage_path)

        assert len(service2._entries) == 1
        assert service2._entries[0].filename == "test.xlsx"

    def test_file_extension_extraction(self, service):
        """Test extracción correcta de extensión."""
        entry1 = service.record_feedback(
            tenant_id="t1",
            original_parser="p1",
            original_confidence=0.9,
            original_doc_type="products",
            corrected_parser=None,
            corrected_doc_type=None,
            was_correct=True,
            headers=[],
            filename="file.XLSX",
        )
        assert entry1.file_extension == "xlsx"

        entry2 = service.record_feedback(
            tenant_id="t1",
            original_parser="p1",
            original_confidence=0.9,
            original_doc_type="products",
            corrected_parser=None,
            corrected_doc_type=None,
            was_correct=True,
            headers=[],
            filename="no_extension",
        )
        assert entry2.file_extension == ""


class TestFeedbackEntry:
    """Test FeedbackEntry dataclass."""

    def test_entry_creation(self):
        """Test creating a FeedbackEntry."""
        entry = FeedbackEntry(
            id="entry-123",
            tenant_id="tenant-1",
            created_at="2024-01-15T10:30:00",
            original_parser="products_excel",
            original_confidence=0.85,
            original_doc_type="products",
            corrected_parser=None,
            corrected_doc_type=None,
            was_correct=True,
            headers=["name", "price"],
            filename="products.xlsx",
            file_extension="xlsx",
            decision_log_id=None,
        )

        assert entry.id == "entry-123"
        assert entry.was_correct is True
        assert entry.headers == ["name", "price"]


class TestFeedbackServiceSingleton:
    """Test singleton instance."""

    def test_singleton_exists(self):
        """Test that singleton is initialized."""
        assert feedback_service is not None
        assert isinstance(feedback_service, FeedbackService)

    def test_singleton_has_storage_path(self):
        """Test that singleton has storage path."""
        assert hasattr(feedback_service, "storage_path")
