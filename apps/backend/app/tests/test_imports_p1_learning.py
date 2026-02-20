"""
P1 Regression tests: Auto-learning, confidence gating, telemetry, accounting normalization.
"""

from uuid import uuid4

import pytest

from app.modules.imports.domain import (
    AccountingNormalizer,
    ConfidenceGate,
    ConfidenceGatingPolicy,
    ConfidenceLevel,
    FeedbackType,
    MappingFeedback,
    MappingLearner,
    MetricType,
    QualityTelemetryCollector,
)


class TestMappingFeedback:
    """Test mapping feedback and learning."""

    def test_create_mapping_feedback(self):
        """Test creating feedback for mapping."""
        feedback = MappingFeedback(
            tenant_id=uuid4(),
            doc_type="sales_invoice",
            headers=["Factura", "Fecha", "Cliente", "Total"],
            feedback_type=FeedbackType.ACCEPTED,
            user_id=uuid4(),
        )

        assert feedback.doc_type == "sales_invoice"
        assert len(feedback.headers) == 4
        assert feedback.feedback_type == FeedbackType.ACCEPTED

    def test_mark_field_correct(self):
        """Test marking a field mapping as correct."""
        feedback = MappingFeedback(
            tenant_id=uuid4(),
            doc_type="sales_invoice",
            headers=["Factura", "Fecha", "Cliente", "Total"],
        )

        feedback.mark_field_correct("Factura", "invoice_number")

        assert "Factura" in feedback.field_feedbacks
        assert feedback.field_feedbacks["Factura"].was_correct is True

    def test_mark_field_corrected(self):
        """Test marking field mapping as corrected by user."""
        feedback = MappingFeedback(
            tenant_id=uuid4(),
            doc_type="sales_invoice",
            headers=["Factura", "Fecha", "Cliente", "Total"],
        )

        feedback.mark_field_corrected("Factura", "invoice_date", "invoice_number")

        assert feedback.feedback_type == FeedbackType.CORRECTED
        assert feedback.field_feedbacks["Factura"].user_corrected_to == "invoice_number"
        assert feedback.field_feedbacks["Factura"].was_correct is False


class TestMappingLearner:
    """Test learning from mapping feedback."""

    def test_learn_from_feedback(self):
        """Test that learner records feedback."""
        learner = MappingLearner()
        tenant_id = uuid4()

        feedback = MappingFeedback(
            tenant_id=tenant_id,
            doc_type="sales_invoice",
            headers=["Factura", "Fecha", "Total"],
        )
        feedback.mark_field_correct("Factura", "invoice_number")
        feedback.mark_field_correct("Fecha", "invoice_date")
        feedback.mark_field_correct("Total", "amount_total")

        learner.record_feedback(feedback)

        # Check stats were recorded
        assert tenant_id in learner.mapping_stats
        assert "sales_invoice" in learner.mapping_stats[tenant_id]

    def test_get_mapping_confidence(self):
        """Test getting confidence for a specific mapping."""
        learner = MappingLearner()
        tenant_id = uuid4()

        # Record several correct mappings
        for _ in range(3):
            feedback = MappingFeedback(tenant_id=tenant_id, doc_type="sales_invoice")
            feedback.mark_field_correct("Factura", "invoice_number")
            learner.record_feedback(feedback)

        # Check confidence is high
        confidence = learner.get_mapping_confidence(
            tenant_id=tenant_id,
            doc_type="sales_invoice",
            header="Factura",
            canonical="invoice_number",
        )

        assert confidence > 0.5  # Should learn from experience

    def test_get_suggested_mapping_improved(self):
        """Test that suggestions improve after learning."""
        learner = MappingLearner()
        tenant_id = uuid4()

        # Simulate learning: "Factura" should map to "invoice_number"
        for _ in range(5):
            feedback = MappingFeedback(tenant_id=tenant_id, doc_type="sales_invoice")
            feedback.mark_field_correct("Factura", "invoice_number")
            learner.record_feedback(feedback)

        # Now get suggestion with baseline that suggests something different
        baseline = {
            "Factura": "description",  # Wrong baseline
            "Fecha": "invoice_date",
        }

        suggestion = learner.get_suggested_mapping(
            tenant_id=tenant_id,
            doc_type="sales_invoice",
            headers=["Factura", "Fecha"],
            baseline_mapping=baseline,
        )

        # Learner should override with correct mapping
        assert suggestion["Factura"] == "invoice_number"

    def test_get_top_candidates(self):
        """Test getting top candidate mappings."""
        learner = MappingLearner()
        tenant_id = uuid4()

        # Record different mappings for same header
        feedback1 = MappingFeedback(tenant_id=tenant_id, doc_type="sales_invoice")
        feedback1.mark_field_correct("Amount", "amount_total")
        learner.record_feedback(feedback1)

        feedback2 = MappingFeedback(tenant_id=tenant_id, doc_type="sales_invoice")
        feedback2.mark_field_correct("Amount", "amount_subtotal")
        learner.record_feedback(feedback2)

        # Check top candidates
        candidates = learner.get_top_candidates(
            tenant_id=tenant_id,
            doc_type="sales_invoice",
            header="Amount",
            top_n=3,
        )

        assert len(candidates) > 0
        assert candidates[0][0] in ["amount_total", "amount_subtotal"]


class TestConfidenceGating:
    """Test confidence-based gating."""

    def test_create_confidence_gate(self):
        """Test creating a confidence gate."""
        gate = ConfidenceGate(
            document_id="doc-1",
            doc_type="sales_invoice",
            parser_confidence=0.95,
            doc_type_confidence=0.90,
            mapping_confidence=0.85,
            validation_confidence=0.92,
        )

        gate.calculate_overall()

        assert gate.overall_confidence > 0.5
        assert gate.confidence_level != ConfidenceLevel.UNKNOWN

    def test_high_confidence(self):
        """Test high confidence gate."""
        gate = ConfidenceGate(
            document_id="doc-1",
            doc_type="sales_invoice",
            parser_confidence=0.95,
            doc_type_confidence=0.95,
            mapping_confidence=0.90,
            validation_confidence=0.95,
        )

        gate.calculate_overall()

        assert gate.should_auto_approve()
        assert not gate.requires_confirmation()

    def test_low_confidence_blocks_promotion(self):
        """Test low confidence blocks promotion."""
        gate = ConfidenceGate(
            document_id="doc-1",
            doc_type="sales_invoice",
            parser_confidence=0.50,
            doc_type_confidence=0.60,
            mapping_confidence=0.55,
            validation_confidence=0.65,
        )

        gate.calculate_overall()

        assert gate.should_block_promotion()
        assert gate.requires_confirmation()

    def test_medium_confidence_requires_confirm(self):
        """Test medium confidence requires confirmation."""
        gate = ConfidenceGate(
            document_id="doc-1",
            doc_type="sales_invoice",
            parser_confidence=0.75,
            doc_type_confidence=0.75,
            mapping_confidence=0.72,
            validation_confidence=0.78,
        )

        gate.calculate_overall()

        assert gate.requires_confirmation()
        assert not gate.should_auto_approve()
        assert not gate.should_block_promotion()


class TestConfidencePolicy:
    """Test confidence gating policy."""

    def test_policy_evaluation(self):
        """Test policy evaluates gates correctly."""
        policy = ConfidenceGatingPolicy()

        gate = ConfidenceGate(
            document_id="doc-1",
            doc_type="sales_invoice",
            parser_confidence=0.95,
            doc_type_confidence=0.92,
            mapping_confidence=0.90,
            validation_confidence=0.94,
        )

        result = policy.evaluate(gate)

        assert result["action"] == "auto_approve"
        assert "overall_confidence" in result
        assert "components" in result


class TestAccountingNormalizer:
    """Test accounting field normalization."""

    def test_normalize_expense(self):
        """Test normalizing expense fields."""
        normalizer = AccountingNormalizer()

        data = {
            "expense_date": "2024-01-15",
            "description": "Office supplies",
            "amount": "150.50",
        }

        normalized, mapping = normalizer.normalize(data, "expense")

        assert "expense_date" in normalized
        assert "amount" in normalized
        assert normalized["expense_date"] == "2024-01-15"

    def test_fallback_date_field(self):
        """Test fallback date field detection."""
        normalizer = AccountingNormalizer()

        # Missing expense_date, have posting_date instead
        data = {
            "posting_date": "2024-01-20",
            "description": "Something",
            "amount": "100.00",
        }

        normalized, mapping = normalizer.normalize(data, "expense")

        # Should use fallback
        assert normalized.get("expense_date") == "2024-01-20"

    def test_fallback_amount_field(self):
        """Test fallback amount field detection."""
        normalizer = AccountingNormalizer()

        # Missing amount, have total_amount
        data = {
            "expense_date": "2024-01-15",
            "description": "Something",
            "total_amount": 250.75,
        }

        normalized, mapping = normalizer.normalize(data, "expense")

        # Should use fallback amount
        assert normalized.get("amount") is not None

    def test_validate_normalization(self):
        """Test validation of mandatory fields."""
        normalizer = AccountingNormalizer()

        # Missing mandatory fields
        data = {
            "description": "Something",
        }

        errors = normalizer.validate_normalization(data, "expense")

        assert "expense_date" in errors
        assert "amount" in errors


class TestQualityTelemetry:
    """Test quality telemetry collection."""

    def test_record_parser_decision(self):
        """Test recording parser decisions."""
        collector = QualityTelemetryCollector()
        tenant_id = "tenant-1"

        collector.record_parser_decision(
            tenant_id=tenant_id,
            suggested_parser="xlsx_invoices",
            doc_type="sales_invoice",
            is_correct=True,
        )

        summary = collector.get_metric_summary(tenant_id)

        assert MetricType.PARSER_ACCURACY.value in summary

    def test_get_accuracy_by_doc_type(self):
        """Test getting accuracy breakdown by doc type."""
        collector = QualityTelemetryCollector()
        tenant_id = "tenant-1"

        # Record metrics for different doc types
        for _ in range(3):
            collector.record_doc_type_classification(
                tenant_id=tenant_id,
                suggested_doc_type="sales_invoice",
                actual_doc_type="sales_invoice",
                confidence=0.95,
            )

        for _ in range(2):
            collector.record_doc_type_classification(
                tenant_id=tenant_id,
                suggested_doc_type="expense",
                actual_doc_type="expense",
                confidence=0.85,
            )

        accuracy_by_type = collector.get_accuracy_by_doc_type(tenant_id)

        assert "sales_invoice" in accuracy_by_type
        assert "expense" in accuracy_by_type

    def test_trend_analysis(self):
        """Test trend analysis."""
        collector = QualityTelemetryCollector()
        tenant_id = "tenant-1"

        # Record improving trend
        for i in range(3):
            collector.record_doc_type_classification(
                tenant_id=tenant_id,
                suggested_doc_type="sales_invoice",
                actual_doc_type="sales_invoice",
                confidence=0.7 + (i * 0.1),  # 0.7, 0.8, 0.9
            )

        trends = collector.get_trend_analysis(tenant_id)

        assert MetricType.DOC_TYPE_ACCURACY.value in trends

    def test_record_multiple_metrics(self):
        """Test recording multiple metrics."""
        collector = QualityTelemetryCollector()
        tenant_id = "tenant-1"

        collector.record_parser_decision(tenant_id, "parser1", "sales_invoice", True)
        collector.record_doc_type_classification(tenant_id, "sales_invoice", "sales_invoice", 0.95)
        collector.record_mapping_accuracy(tenant_id, "sales_invoice", 4, 4)
        collector.record_validation_result(tenant_id, "sales_invoice", True)
        collector.record_manual_correction(tenant_id, "sales_invoice", False)

        summary = collector.get_metric_summary(tenant_id)

        # Should have multiple metrics
        assert len(summary) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
