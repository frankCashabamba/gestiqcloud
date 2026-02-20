from uuid import UUID

from app.modules.imports.application.canonical_mapper import CanonicalMapper
from app.modules.imports.application.ingest_service import IngestService
from app.modules.imports.application.learning_loop import ActiveLearning
from app.modules.imports.application.scoring_engine import ScoringEngine
from app.modules.imports.application.smart_router import SmartRouter
from app.modules.imports.domain.interfaces import DocType, ParseResult
from app.modules.imports.infrastructure.country_packs import create_registry
from app.modules.imports.infrastructure.learning_store import InMemoryLearningStore
from app.modules.imports.infrastructure.validators import InvoiceValidator


def example_sprint1_basic_flow():
    print("\n=== SPRINT 1: Basic Ingest Flow ===")

    SmartRouter()
    service = IngestService()

    tenant_id = UUID("00000000-0000-0000-0000-000000000000")

    batch_id = service.create_batch(
        tenant_id=tenant_id,
        source_type="invoices",
        origin="excel",
        file_key="file_123.xlsx",
    )
    print(f"Created batch: {batch_id}")

    mock_parse_result = ParseResult(
        items=[
            {"invoice_number": "INV001", "amount": 150.0, "tax_id": "123456"},
            {"invoice_number": "INV002", "amount": 200.0, "tax_id": "654321"},
        ],
        doc_type=DocType.INVOICE,
        metadata={"source": "excel"},
        parse_errors=[],
    )

    item_ids = service.ingest_parse_result(batch_id, mock_parse_result)
    print(f"Ingested {len(item_ids)} items")

    batch_status = service.get_batch_status(batch_id)
    print(f"Batch status: {batch_status['status']}, items: {batch_status['total_items']}")


def example_sprint2_classification():
    print("\n=== SPRINT 2: Classification & Scoring ===")

    scoring_engine = ScoringEngine()

    def invoice_rule(data):
        score = 0.0
        if "invoice_number" in data:
            score += 0.3
        if "amount" in data:
            score += 0.3
        if "tax_id" in data:
            score += 0.4
        return min(score, 1.0)

    scoring_engine.register_rule("invoice", invoice_rule)

    raw_data = {"invoice_number": "INV001", "amount": 150.0, "tax_id": "123456"}
    result = scoring_engine.classify(raw_data)

    print(f"Doc Type: {result.doc_type.value}")
    print(f"Confidence: {result.confidence.value} ({result.confidence_score:.2f})")

    explanation = scoring_engine.score_with_explanation(raw_data)
    print(f"All scores: {explanation['all_scores']}")


def example_sprint2_mapping():
    print("\n=== SPRINT 2: Field Mapping ===")

    mapper = CanonicalMapper()

    mapping = {
        "invoice_number": ["numero", "número", "invoice_no"],
        "invoice_date": ["fecha", "date"],
        "amount": ["monto", "importe", "total"],
    }
    mapper.register_field_mapping(DocType.INVOICE.value, mapping)

    raw_data = {
        "numero": "INV001",
        "fecha": "2024-01-15",
        "monto": 150.0,
        "extra_field": "value",
    }

    result = mapper.map_fields(raw_data, DocType.INVOICE)

    print(f"Normalized: {result.normalized_data}")
    print(f"Mapped fields: {result.mapped_fields}")
    print(f"Unmapped: {result.unmapped_fields}")


def example_sprint3_country_validation():
    print("\n=== SPRINT 3: Country-Specific Validation ===")

    registry = create_registry()

    ec_pack = registry.get("EC")
    print(f"Ecuador config: {ec_pack.get_country_code()}, Currency: {ec_pack.get_currency()}")

    valid, error = ec_pack.validate_tax_id("1234567890")
    print(f"Tax ID 1234567890 valid: {valid}")

    valid, error = ec_pack.validate_date_format("01/01/2024")
    print(f"Date 01/01/2024 valid: {valid}")

    invoice_data = {
        "invoice_number": "INV001",
        "amount": 100.0,
        "tax_id": "1234567890",
        "invoice_date": "01/01/2024",
        "currency": "USD",
    }

    fiscal_errors = ec_pack.validate_fiscal_fields(invoice_data)
    print(f"Fiscal validation errors: {fiscal_errors}")

    validator = InvoiceValidator(ec_pack)
    validation_errors = validator.validate(invoice_data, DocType.INVOICE)
    print(f"Full validation errors: {validation_errors}")


def example_sprint4_learning():
    print("\n=== SPRINT 4: Active Learning ===")

    learning_store = InMemoryLearningStore()
    scoring_engine = ScoringEngine()

    active_learning = ActiveLearning(learning_store, scoring_engine)

    training_data = [
        {
            "raw_data": {"invoice_number": "INV001", "amount": 100.0},
            "correct_doc_type": DocType.INVOICE,
            "original_doc_type": DocType.EXPENSE_RECEIPT,
            "confidence_was": 0.45,
        },
        {
            "raw_data": {"recibo": "REC001", "monto": 50.0},
            "correct_doc_type": DocType.EXPENSE_RECEIPT,
            "original_doc_type": DocType.INVOICE,
            "confidence_was": 0.42,
        },
    ]

    for sample in training_data:
        active_learning.add_training_sample(
            raw_data=sample["raw_data"],
            correct_doc_type=sample["correct_doc_type"],
            original_doc_type=sample["original_doc_type"],
            confidence_was=sample["confidence_was"],
        )

    print(f"Training samples: {active_learning.get_training_stats()}")

    misclass = learning_store.get_misclassification_stats()
    print(f"Misclassifications: {misclass}")

    should_retrain = active_learning.should_retrain(min_samples=1)
    print(f"Should retrain: {should_retrain}")


def example_end_to_end_flow():
    print("\n=== COMPLETE END-TO-END FLOW ===")

    print("1. Initialize systems...")
    SmartRouter()
    service = IngestService()
    scoring_engine = ScoringEngine()
    mapper = CanonicalMapper()
    registry = create_registry()
    InMemoryLearningStore()

    print("2. Create batch...")
    batch_id = service.create_batch(
        tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
        source_type="invoices",
        origin="excel",
    )

    print("3. Ingest file...")
    parse_result = ParseResult(
        items=[{"numero": "INV001", "monto": 100.0, "ruc": "1234567890"}],
        doc_type=DocType.INVOICE,
        metadata={},
        parse_errors=[],
    )

    item_ids = service.ingest_parse_result(batch_id, parse_result)

    print("4. Classify...")
    for item_id in item_ids:
        item = service.items[item_id]
        classify_result = scoring_engine.classify(item["raw"])
        service.update_item_after_classify(item_id, classify_result)
        print(f"   Item {item_id}: {classify_result.doc_type.value}")

    print("5. Map fields...")
    mapping = {
        "invoice_number": ["numero"],
        "amount": ["monto"],
        "tax_id": ["ruc"],
    }
    mapper.register_field_mapping(DocType.INVOICE.value, mapping)

    for item_id in item_ids:
        item = service.items[item_id]
        map_result = mapper.map_fields(item["raw"], DocType.INVOICE)
        service.update_item_after_map(item_id, map_result)
        print(f"   Item {item_id}: {map_result.mapped_fields}")

    print("6. Validate (with country rules)...")
    ec_pack = registry.get("EC")
    validator = InvoiceValidator(ec_pack)

    for item_id in item_ids:
        item = service.items[item_id]
        errors = validator.validate(item["normalized"], DocType.INVOICE)
        print(f"   Item {item_id}: {len(errors)} errors")

    print("✓ End-to-end flow complete")


if __name__ == "__main__":
    example_sprint1_basic_flow()
    example_sprint2_classification()
    example_sprint2_mapping()
    example_sprint3_country_validation()
    example_sprint4_learning()
    example_end_to_end_flow()
