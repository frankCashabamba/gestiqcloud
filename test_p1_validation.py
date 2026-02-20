#!/usr/bin/env python3
"""P1 quick validation."""

import sys
sys.path.insert(0, "./apps/backend")

from uuid import uuid4
from app.modules.imports.domain import (
    MappingLearner,
    MappingFeedback,
    FeedbackType,
    ConfidenceGate,
    ConfidenceLevel,
    ConfidenceGatingPolicy,
    AccountingNormalizer,
    QualityTelemetryCollector,
    MetricType,
)

print("[OK] Testing P1 features...")

# 1. Test Auto-learning Mapping
print("\n1. Testing auto-learning mapping...")
learner = MappingLearner()
tenant_id = uuid4()

feedback = MappingFeedback(
    tenant_id=tenant_id,
    doc_type="sales_invoice",
    headers=["Numero de Factura", "Fecha"],
)
feedback.mark_field_correct("Numero de Factura", "invoice_number")
feedback.mark_field_correct("Fecha", "invoice_date")
learner.record_feedback(feedback)

# Check learning
confidence = learner.get_mapping_confidence(
    tenant_id=tenant_id,
    doc_type="sales_invoice",
    header="Numero de Factura",
    canonical="invoice_number",
)
assert confidence > 0.0
print("  [OK] Auto-learning mapping works")

# 2. Test Confidence Gating
print("\n2. Testing confidence gating...")
gate = ConfidenceGate(
    document_id="doc-1",
    doc_type="sales_invoice",
    parser_confidence=0.95,
    doc_type_confidence=0.92,
    mapping_confidence=0.90,
    validation_confidence=0.94,
)
gate.calculate_overall()

assert gate.should_auto_approve()
assert not gate.requires_confirmation()
print("  [OK] High confidence auto-approves")

gate_low = ConfidenceGate(
    document_id="doc-2",
    doc_type="sales_invoice",
    parser_confidence=0.50,
    doc_type_confidence=0.60,
    mapping_confidence=0.55,
    validation_confidence=0.65,
)
gate_low.calculate_overall()

assert gate_low.should_block_promotion()
print("  [OK] Low confidence blocks promotion")

# 3. Test Policy Evaluation
print("\n3. Testing confidence policy...")
policy = ConfidenceGatingPolicy()
result = policy.evaluate(gate)

assert result["action"] == "auto_approve"
assert "overall_confidence" in result
print("  [OK] Policy evaluation works")

# 4. Test Accounting Normalization
print("\n4. Testing accounting normalization...")
normalizer = AccountingNormalizer()

# Complete data
data = {
    "expense_date": "2024-01-15",
    "description": "Office supplies",
    "amount": "150.50",
}
normalized, mapping = normalizer.normalize(data, "expense")
assert normalized["expense_date"] is not None
assert normalized["amount"] is not None
print("  [OK] Complete expense normalizes")

# Missing date - use fallback
data_missing_date = {
    "posting_date": "2024-01-20",
    "description": "Something",
    "amount": "100.00",
}
normalized2, _ = normalizer.normalize(data_missing_date, "expense")
assert normalized2.get("expense_date") is not None
print("  [OK] Missing date falls back to posting_date")

# 5. Test Quality Telemetry
print("\n5. Testing quality telemetry...")
collector = QualityTelemetryCollector()
tenant_id = "tenant-1"

collector.record_doc_type_classification(
    tenant_id=tenant_id,
    suggested_doc_type="sales_invoice",
    actual_doc_type="sales_invoice",
    confidence=0.95,
)

summary = collector.get_metric_summary(tenant_id)
assert MetricType.DOC_TYPE_ACCURACY.value in summary
print("  [OK] Telemetry collection works")

accuracy_by_type = collector.get_accuracy_by_doc_type(tenant_id)
assert "sales_invoice" in accuracy_by_type
print("  [OK] Accuracy by type works")

print("\n" + "="*50)
print("[OK] ALL P1 TESTS PASSED")
print("="*50)
