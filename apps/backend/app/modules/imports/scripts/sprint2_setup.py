import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.modules.imports.application.smart_router import SmartRouter
from app.modules.imports.application.scoring_engine import ScoringEngine
from app.modules.imports.application.quality_gates import QualityGate
from app.modules.imports.application.observability import MetricsCollector, RollbackManager
from app.modules.imports.infrastructure.learning_store import InMemoryLearningStore


def setup_scoring_engine_v2() -> ScoringEngine:
    engine = ScoringEngine()

    def advanced_invoice_rule(raw_data: dict) -> float:
        score = 0.0
        required_fields = ["invoice_number", "invoice_date", "amount", "tax_id"]
        for field in required_fields:
            if field in raw_data and raw_data[field]:
                score += 0.15
        return min(score, 1.0)

    def advanced_expense_rule(raw_data: dict) -> float:
        score = 0.0
        keywords = ["recibo", "receipt", "gasto", "expense", "comprobante"]
        text = " ".join(str(v).lower() for v in raw_data.values())
        for kw in keywords:
            if kw in text:
                score += 0.15
        return min(score, 1.0)

    def advanced_bank_rule(raw_data: dict) -> float:
        score = 0.0
        bank_fields = ["account", "bank", "balance", "transaction_date"]
        for field in bank_fields:
            if field in raw_data and raw_data[field]:
                score += 0.15
        return min(score, 1.0)

    engine.register_rule("invoice", advanced_invoice_rule)
    engine.register_rule("expense_receipt", advanced_expense_rule)
    engine.register_rule("bank_statement", advanced_bank_rule)

    return engine


def setup_quality_gates() -> QualityGate:
    return QualityGate(min_precision=0.85, min_recall=0.80)


def setup_metrics_collector() -> MetricsCollector:
    return MetricsCollector()


def setup_rollback_manager() -> RollbackManager:
    return RollbackManager()


def setup_learning_store() -> InMemoryLearningStore:
    return InMemoryLearningStore()


if __name__ == "__main__":
    print("Setting up Sprint 2 Scoring & Observability...")

    scoring_engine = setup_scoring_engine_v2()
    print("✓ Scoring engine v2 initialized")

    quality_gate = setup_quality_gates()
    print(f"✓ Quality gate configured (precision: {quality_gate.min_precision}, recall: {quality_gate.min_recall})")

    metrics = setup_metrics_collector()
    print("✓ Metrics collector initialized")

    rollback = setup_rollback_manager()
    print("✓ Rollback manager initialized")

    learning = setup_learning_store()
    print("✓ Learning store initialized")

    print("✓ Sprint 2 setup complete")
    print("  - Advanced scoring rules registered")
    print("  - Quality gates configured")
    print("  - Metrics collection enabled")
    print("  - Rollback capability ready")
