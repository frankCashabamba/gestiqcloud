import pytest
from uuid import UUID

from app.modules.imports.application.smart_router import SmartRouter
from app.modules.imports.application.ingest_service import IngestService, BatchStatus
from app.modules.imports.application.scoring_engine import ScoringEngine
from app.modules.imports.application.canonical_mapper import CanonicalMapper
from app.modules.imports.domain.interfaces import DocType, ConfidenceLevel, ItemStatus
from app.modules.imports.infrastructure.country_packs import create_registry
from app.modules.imports.infrastructure.validators import InvoiceValidator
from app.modules.imports.infrastructure.learning_store import InMemoryLearningStore
from app.modules.imports.application.learning_loop import ActiveLearning
from app.modules.imports.application.observability import MetricsCollector
from app.modules.imports.application.quality_gates import QualityGate


@pytest.fixture
def smart_router():
    return SmartRouter()


@pytest.fixture
def ingest_service():
    return IngestService()


@pytest.fixture
def scoring_engine():
    return ScoringEngine()


@pytest.fixture
def mapper():
    return CanonicalMapper()


@pytest.fixture
def country_registry():
    return create_registry()


@pytest.fixture
def learning_store():
    return InMemoryLearningStore()


@pytest.fixture
def metrics_collector():
    return MetricsCollector()


class TestSprint1Foundation:
    def test_smart_router_initialization(self, smart_router):
        assert smart_router is not None
        assert len(smart_router.parsers) == 0

    def test_batch_creation(self, ingest_service):
        batch_id = ingest_service.create_batch(
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
            source_type="invoices",
            origin="excel",
        )

        assert batch_id is not None
        assert batch_id in ingest_service.batches

        batch = ingest_service.batches[batch_id]
        assert batch["status"] == BatchStatus.PENDING.value
        assert batch["source_type"] == "invoices"

    def test_item_status_transitions(self, ingest_service):
        batch_id = ingest_service.create_batch(
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
            source_type="invoices",
            origin="excel",
        )

        from app.modules.imports.domain.interfaces import ParseResult

        parse_result = ParseResult(
            items=[{"invoice_number": "INV001", "amount": 100.0}],
            doc_type=DocType.INVOICE,
            metadata={},
            parse_errors=[],
        )

        item_ids = ingest_service.ingest_parse_result(batch_id, parse_result)
        assert len(item_ids) > 0

        item = ingest_service.items[item_ids[0]]
        assert item["status"] == ItemStatus.PENDING.value

    def test_batch_status_after_ingest(self, ingest_service):
        batch_id = ingest_service.create_batch(
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
            source_type="invoices",
            origin="excel",
        )

        from app.modules.imports.domain.interfaces import ParseResult

        parse_result = ParseResult(
            items=[{"invoice_number": "INV001", "amount": 100.0}],
            doc_type=DocType.INVOICE,
            metadata={},
            parse_errors=[],
        )

        ingest_service.ingest_parse_result(batch_id, parse_result)

        status = ingest_service.get_batch_status(batch_id)
        assert status["status"] == BatchStatus.INGESTED.value
        assert status["total_items"] == 1

    def test_correction_recording(self, ingest_service):
        batch_id = ingest_service.create_batch(
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
            source_type="invoices",
            origin="excel",
        )

        from app.modules.imports.domain.interfaces import ParseResult

        parse_result = ParseResult(
            items=[{"invoice_number": "INV001"}],
            doc_type=DocType.INVOICE,
            metadata={},
            parse_errors=[],
        )

        item_ids = ingest_service.ingest_parse_result(batch_id, parse_result)
        item_id = item_ids[0]

        ingest_service.record_correction(
            item_id, "invoice_number", "INV001", "INV002"
        )

        item = ingest_service.items[item_id]
        assert "last_correction" in item
        assert item["last_correction"]["invoice_number"]["new"] == "INV002"


class TestSprint2Scoring:
    def test_scoring_engine_classify(self, scoring_engine):
        result = scoring_engine.classify(
            {"invoice_number": "INV001", "amount": 100.0}
        )

        assert result.doc_type is not None
        assert result.confidence is not None
        assert 0.0 <= result.confidence_score <= 1.0

    def test_confidence_levels(self, scoring_engine):
        low_conf = scoring_engine._score_to_confidence(0.3)
        assert low_conf == ConfidenceLevel.LOW

        med_conf = scoring_engine._score_to_confidence(0.65)
        assert med_conf == ConfidenceLevel.MEDIUM

        high_conf = scoring_engine._score_to_confidence(0.9)
        assert high_conf == ConfidenceLevel.HIGH

    def test_fingerprinting(self, scoring_engine):
        data1 = {"a": 1, "b": "text"}
        data2 = {"a": 2, "b": "text"}
        data3 = {"a": 1, "b": "text", "c": 3}

        fp1 = scoring_engine._compute_fingerprint(data1)
        fp2 = scoring_engine._compute_fingerprint(data2)
        fp3 = scoring_engine._compute_fingerprint(data3)

        assert fp1 == fp2
        assert fp1 != fp3

    def test_score_with_explanation(self, scoring_engine):
        result = scoring_engine.score_with_explanation(
            {"invoice_number": "INV001", "amount": 100.0}
        )

        assert "doc_type" in result
        assert "confidence" in result
        assert "explanation" in result
        assert "all_scores" in result

    def test_mapper_field_normalization(self, mapper):
        result = mapper.map_fields(
            {"numero": 123, "fecha": "2024-01-01", "monto": 100.0},
            DocType.INVOICE,
        )

        assert result is not None
        assert result.doc_type == DocType.INVOICE


class TestSprint3CountryPacks:
    def test_country_registry_initialization(self, country_registry):
        countries = country_registry.list_all()
        assert len(countries) > 0
        assert "EC" in countries
        assert "ES" in countries

    def test_ecuador_pack(self, country_registry):
        ec_pack = country_registry.get("EC")
        assert ec_pack is not None
        assert ec_pack.get_country_code() == "EC"
        assert ec_pack.get_currency() == "USD"

    def test_spain_pack(self, country_registry):
        es_pack = country_registry.get("ES")
        assert es_pack is not None
        assert es_pack.get_country_code() == "ES"
        assert es_pack.get_currency() == "EUR"

    def test_tax_id_validation(self, country_registry):
        ec_pack = country_registry.get("EC")
        valid, error = ec_pack.validate_tax_id("1234567890")
        assert valid is True

        valid, error = ec_pack.validate_tax_id("invalid")
        assert valid is False

    def test_date_validation(self, country_registry):
        ec_pack = country_registry.get("EC")
        valid, error = ec_pack.validate_date_format("01/01/2024")
        assert valid is True

        valid, error = ec_pack.validate_date_format("invalid")
        assert valid is False

    def test_validator_with_country_pack(self, country_registry):
        ec_pack = country_registry.get("EC")
        validator = InvoiceValidator(ec_pack)

        errors = validator.validate(
            {"invoice_number": "INV001", "tax_id": "1234567890"},
            DocType.INVOICE,
        )

        assert isinstance(errors, list)


class TestSprint4Learning:
    def test_learning_store_record_correction(self, learning_store):
        learning_store.record_correction(
            batch_id="batch1",
            item_idx=0,
            original_doc_type=DocType.EXPENSE_RECEIPT,
            corrected_doc_type=DocType.INVOICE,
            confidence_was=0.5,
        )

        assert len(learning_store.corrections) > 0

    def test_misclassification_stats(self, learning_store):
        learning_store.record_correction(
            batch_id="batch1",
            item_idx=0,
            original_doc_type=DocType.EXPENSE_RECEIPT,
            corrected_doc_type=DocType.INVOICE,
            confidence_was=0.5,
        )

        stats = learning_store.get_misclassification_stats()
        assert "expense_receipt_to_invoice" in stats

    def test_active_learning(self, scoring_engine, learning_store):
        active_learning = ActiveLearning(learning_store, scoring_engine)

        active_learning.add_training_sample(
            raw_data={"invoice_number": "INV001"},
            correct_doc_type=DocType.INVOICE,
            original_doc_type=DocType.EXPENSE_RECEIPT,
            confidence_was=0.4,
        )

        stats = active_learning.get_training_stats()
        assert stats["total_samples"] == 1

    def test_quality_gate_evaluation(self):
        gate = QualityGate(min_precision=0.85, min_recall=0.80)

        from app.modules.imports.application.quality_gates import QualityMetrics

        metrics = QualityMetrics(
            total_samples=100,
            correct_classifications=90,
            precision=0.90,
            recall=0.90,
            f1_score=0.90,
            timestamp="2024-01-01",
        )

        passed, message = gate.evaluate(metrics)
        assert passed is True

    def test_metrics_collection(self, metrics_collector):
        metrics_collector.record_classification(
            doc_type="invoice",
            confidence=0.95,
            processing_time_ms=150.0,
            success=True,
        )

        summary = metrics_collector.get_metrics_summary()
        assert summary["doc_types_tracked"] > 0
        assert "invoice" in summary["buckets"]

    def test_metrics_by_doc_type(self, metrics_collector):
        metrics_collector.record_classification(
            doc_type="invoice",
            confidence=0.95,
            processing_time_ms=150.0,
            success=True,
        )

        metrics = metrics_collector.get_metrics_by_doc_type("invoice")
        assert metrics is not None
        assert metrics["total_processed"] == 1
        assert metrics["success_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
