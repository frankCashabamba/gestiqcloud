import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.modules.imports.infrastructure.learning_store import InMemoryLearningStore, JsonFilelearningStore
from app.modules.imports.application.learning_loop import ActiveLearning, IncrementalTrainer
from app.modules.imports.application.quality_gates import QualityGate, CIQualityCheck
from app.modules.imports.application.observability import MetricsCollector, RollbackManager
from app.modules.imports.application.scoring_engine import ScoringEngine


def setup_learning_pipeline(classifier: ScoringEngine) -> dict:
    learning_store = InMemoryLearningStore()

    active_learning = ActiveLearning(learning_store, classifier)

    incremental_trainer = IncrementalTrainer()
    incremental_trainer.schedule_training(frequency="weekly")

    ci_check = CIQualityCheck()

    return {
        "learning_store": learning_store,
        "active_learning": active_learning,
        "incremental_trainer": incremental_trainer,
        "ci_check": ci_check,
    }


def setup_observability() -> dict:
    metrics = MetricsCollector()

    rollback = RollbackManager()

    return {
        "metrics": metrics,
        "rollback": rollback,
    }


def setup_regression_dataset() -> list[dict]:
    return [
        {
            "raw_data": {"invoice_number": "INV001", "amount": 100.0, "tax_id": "123456"},
            "expected_doc_type": "invoice",
        },
        {
            "raw_data": {"recibo": "REC001", "monto": 50.0},
            "expected_doc_type": "expense_receipt",
        },
        {
            "raw_data": {"cuenta": "ACC123", "banco": "BANCO", "balance": 1000.0},
            "expected_doc_type": "bank_statement",
        },
        {
            "raw_data": {"producto": "PROD001", "precio": 25.5, "stock": 100},
            "expected_doc_type": "product_list",
        },
    ]


if __name__ == "__main__":
    print("Setting up Sprint 4 Learning & Quality Infrastructure...")

    from app.modules.imports.application.scoring_engine import ScoringEngine

    classifier = ScoringEngine()

    learning_config = setup_learning_pipeline(classifier)
    print("✓ Learning pipeline initialized")
    print(f"  - Active learning enabled")
    print(f"  - Incremental trainer scheduled (weekly)")
    print(f"  - CI quality check ready")

    observability_config = setup_observability()
    print("✓ Observability infrastructure set up")
    print(f"  - Metrics collection enabled")
    print(f"  - Rollback management ready")

    regression_dataset = setup_regression_dataset()
    print(f"✓ Regression dataset prepared ({len(regression_dataset)} samples)")

    print("✓ Sprint 4 setup complete")
    print("  - Auto-supervised learning system active")
    print("  - Quality gates monitoring enabled")
    print("  - Metrics & rollback control ready")
