import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.modules.imports.application.adapters import (
    CSVParserAdapter,
    ExcelParserAdapter,
    ImageParserAdapter,
    PDFParserAdapter,
    XMLParserAdapter,
)
from app.modules.imports.application.canonical_mapper import CanonicalMapper
from app.modules.imports.application.scoring_engine import ScoringEngine
from app.modules.imports.application.smart_router import SmartRouter
from app.modules.imports.domain.interfaces import DocType
from app.modules.imports.infrastructure.validators import InvoiceValidator


def setup_smart_router() -> SmartRouter:
    router = SmartRouter()

    def dummy_parser(file_path):
        return {"items": [], "metadata": {}, "errors": []}

    excel_adapter = ExcelParserAdapter("generic_excel", DocType.GENERIC, dummy_parser)
    csv_adapter = CSVParserAdapter("generic_csv", DocType.GENERIC, dummy_parser)
    xml_adapter = XMLParserAdapter("generic_xml", DocType.GENERIC, dummy_parser)
    pdf_adapter = PDFParserAdapter("pdf_ocr", DocType.GENERIC, dummy_parser)
    image_adapter = ImageParserAdapter("image_ocr", DocType.GENERIC, dummy_parser)

    router.register_parser("generic_excel", excel_adapter)
    router.register_parser("generic_csv", csv_adapter)
    router.register_parser("generic_xml", xml_adapter)
    router.register_parser("pdf_ocr", pdf_adapter)
    router.register_parser("image_ocr", image_adapter)

    scoring_engine = ScoringEngine()
    router.register_classifier("hybrid", scoring_engine)

    mapper = CanonicalMapper()
    router.register_mapper("canonical", mapper)

    invoice_validator = InvoiceValidator()
    router.register_validator("strict", invoice_validator)

    return router


def setup_scoring_rules(engine: ScoringEngine) -> None:
    def invoice_rule(raw_data: dict) -> float:
        score = 0.0
        if "invoice_number" in raw_data or "numero" in str(raw_data).lower():
            score += 0.3
        if "invoice_date" in raw_data or "fecha" in str(raw_data).lower():
            score += 0.2
        if "amount" in raw_data or "monto" in str(raw_data).lower():
            score += 0.2
        if "tax" in raw_data or "iva" in str(raw_data).lower():
            score += 0.2
        return min(score, 1.0)

    def expense_rule(raw_data: dict) -> float:
        score = 0.0
        if "recibo" in str(raw_data).lower() or "receipt" in str(raw_data).lower():
            score += 0.5
        if "gasto" in str(raw_data).lower() or "expense" in str(raw_data).lower():
            score += 0.5
        return min(score, 1.0)

    def bank_rule(raw_data: dict) -> float:
        score = 0.0
        if "cuenta" in str(raw_data).lower() or "account" in str(raw_data).lower():
            score += 0.3
        if "banco" in str(raw_data).lower() or "bank" in str(raw_data).lower():
            score += 0.3
        if "saldo" in str(raw_data).lower() or "balance" in str(raw_data).lower():
            score += 0.4
        return min(score, 1.0)

    engine.register_rule("invoice", invoice_rule)
    engine.register_rule("expense_receipt", expense_rule)
    engine.register_rule("bank_statement", bank_rule)

    engine.register_semantic_signal(
        "invoice",
        ["factura", "invoice", "venta", "sales"],
        0.2,
    )
    engine.register_semantic_signal(
        "expense_receipt",
        ["recibo", "gasto", "expense", "receipt"],
        0.2,
    )
    engine.register_semantic_signal(
        "bank_statement",
        ["banco", "transferencia", "bank", "transaction"],
        0.2,
    )


if __name__ == "__main__":
    print("Setting up Sprint 1 Smart Router...")

    router = setup_smart_router()
    print(f"✓ Router initialized with {len(router.parsers)} parsers")

    scoring_engine = ScoringEngine()
    setup_scoring_rules(scoring_engine)
    print("✓ Scoring rules registered")

    print("✓ Sprint 1 setup complete")
    print(f"  - Parsers: {list(router.parsers.keys())}")
    print(f"  - Classifiers: {list(router.classifiers.keys())}")
    print(f"  - Mappers: {list(router.mappers.keys())}")
    print(f"  - Validators: {list(router.validators.keys())}")
