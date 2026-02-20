#!/usr/bin/env python3
"""P2 quick validation."""

import sys
sys.path.insert(0, "./apps/backend")

from uuid import uuid4
from datetime import datetime
from app.modules.imports.domain import (
    ChunkedFileSession,
    StreamingExcelParser,
    LargeFileOptimizer,
    Country,
    PeruRuleSet,
    ColombiaRuleSet,
    country_rules_registry,
    AuditEvent,
    AuditTrail,
    AuditLogger,
    AuditEventType,
    BenchmarkThresholds,
    QualityBenchmark,
    BenchmarkStatus,
)

print("[OK] Testing P2 features...\n")

# 1. Test Large File Handling
print("1. Testing large file handling...")
session = ChunkedFileSession(
    upload_id="upload-1",
    filename="large_file.xlsx",
    total_size=150 * 1024 * 1024,  # 150MB
    chunk_size=10 * 1024 * 1024,  # 10MB chunks
    expected_chunks=15,
    chunks_received={},
)

assert not session.is_complete()
assert len(session.get_missing_chunks()) == 15
print("  [OK] Chunked file session tracking")

# Simulate adding chunks
for i in range(15):
    from app.modules.imports.domain import FileChunk, ChunkStatus
    chunk = FileChunk(
        upload_id="upload-1",
        chunk_number=i,
        size_bytes=10 * 1024 * 1024,
        hash_md5="abcd1234",
        status=ChunkStatus.COMPLETED,
    )
    session.add_chunk(chunk)

assert session.is_complete()
print("  [OK] Complete file detection")

# Test strategy selection
optimizer = LargeFileOptimizer()
strategy = optimizer.get_optimal_strategy(150.0)  # 150MB
assert strategy["strategy"] == "async_worker"
print("  [OK] Large file strategy selection")

# 2. Test Country Rules
print("\n2. Testing country-specific rules...")
peru_rules = PeruRuleSet()

# Test RUC validation
is_valid, error = peru_rules.validate_tax_id("12345678901")  # 11 digits
assert is_valid
print("  [OK] Peru RUC validation")

# Test invalid tax ID
is_valid, error = peru_rules.validate_tax_id("123")
assert not is_valid
print("  [OK] Peru invalid tax ID rejection")

# Test invoice number format
is_valid, error = peru_rules.validate_invoice_number("F-001")
assert is_valid
print("  [OK] Peru invoice number format")

# Test registry
colombia_rules = country_rules_registry.get_rules(Country.CO)
assert colombia_rules is not None
print("  [OK] Colombia rules lookup")

# Test document validation
data = {
    "customer_tax_id": "12345678901",
    "vendor_tax_id": "98765432109",
    "invoice_number": "F-100",
    "amount_subtotal": "1000",
    "amount_tax": "180",  # 18% IGV
}
errors = country_rules_registry.validate_document(Country.PE, "sales_invoice", data)
assert len(errors) == 0
print("  [OK] Full document country validation")

# 3. Test Audit Trail
print("\n3. Testing audit trail...")
logger = AuditLogger()
batch_id = uuid4()
tenant_id = uuid4()

trail = logger.create_trail(tenant_id, batch_id)
logger.log_import_started(trail, "test.xlsx", user_id=uuid4())

assert len(trail.events) == 1
assert trail.events[0].event_type == AuditEventType.IMPORT_STARTED
print("  [OK] Import event logging")

# Log item validation
item_id = uuid4()
logger.log_item_validated(trail, item_id, is_valid=True, error_count=0)
assert len(trail.events) == 2
print("  [OK] Item validation logging")

# Log correction
user_id = uuid4()
logger.log_item_correction(
    trail,
    item_id,
    "invoice_date",
    "2024/01/15",
    "2024-01-15",
    user_id,
    reason="Format standardization",
)
assert len(trail.events) == 3
print("  [OK] Manual correction logging")

# Get timeline
timeline = trail.get_timeline()
assert len(timeline) == 3
print("  [OK] Audit timeline generation")

# Get full report
report = logger.get_full_report(batch_id)
assert "summary" in report
assert "timeline" in report
print("  [OK] Full audit report")

# 4. Test Quality Benchmark
print("\n4. Testing quality benchmark...")
benchmark = QualityBenchmark()

# Simulate metrics
metrics = {
    "parser_accuracy": 92.5,
    "doc_type_accuracy": 89.0,
    "mapping_accuracy": 87.5,
    "validation_pass_rate": 96.0,
    "manual_correction_rate": 8.0,
    "promotion_success_rate": 92.0,
}

sample_sizes = {
    "parser_accuracy": 100,
    "doc_type_accuracy": 100,
    "mapping_accuracy": 100,
    "validation_pass_rate": 100,
    "manual_correction_rate": 100,
    "promotion_success_rate": 100,
}

report = benchmark.evaluate(metrics, sample_sizes, environment="staging")

assert report.overall_status == BenchmarkStatus.PASSED
print("  [OK] Benchmark evaluation - all pass")

# Test failed benchmark
bad_metrics = {
    "parser_accuracy": 70.0,  # Below 90% threshold
    "doc_type_accuracy": 85.0,
    "mapping_accuracy": 80.0,
    "validation_pass_rate": 90.0,
    "manual_correction_rate": 20.0,
    "promotion_success_rate": 80.0,
}

report_fail = benchmark.evaluate(bad_metrics, sample_sizes, environment="staging")
assert report_fail.overall_status == BenchmarkStatus.FAILED
print("  [OK] Benchmark evaluation - failure detection")

# Test deployment decision
decision = benchmark.get_deployment_decision(report_fail)
assert decision["decision"] == "BLOCK"
print("  [OK] Deployment blocking on low quality")

# Test passed decision
decision_pass = benchmark.get_deployment_decision(report)
assert decision_pass["decision"] == "APPROVE"
print("  [OK] Deployment approval on high quality")

print("\n" + "="*50)
print("[OK] ALL P2 TESTS PASSED")
print("="*50)
