#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.imports.scripts import sprint1_setup, sprint2_setup, sprint3_setup, sprint4_setup


def run_all_sprints():
    print("=" * 70)
    print("RUNNING ALL SPRINT SETUPS")
    print("=" * 70)
    print()

    print("SPRINT 1: Foundation & Stabilization")
    print("-" * 70)
    try:
        sprint1_setup.setup_smart_router()
        sprint1_setup.setup_scoring_rules(sprint1_setup.ScoringEngine())
        print("✓ Sprint 1 setup completed successfully")
    except Exception as e:
        print(f"✗ Sprint 1 setup failed: {e}")
    print()

    print("SPRINT 2: Classification & Confidence")
    print("-" * 70)
    try:
        sprint2_setup.setup_scoring_engine_v2()
        sprint2_setup.setup_quality_gates()
        sprint2_setup.setup_metrics_collector()
        sprint2_setup.setup_rollback_manager()
        sprint2_setup.setup_learning_store()
        print("✓ Sprint 2 setup completed successfully")
    except Exception as e:
        print(f"✗ Sprint 2 setup failed: {e}")
    print()

    print("SPRINT 3: Country Packs & Validation")
    print("-" * 70)
    try:
        registry = sprint3_setup.setup_country_registry()
        sprint3_setup.setup_country_validators(registry)
        print("✓ Sprint 3 setup completed successfully")
    except Exception as e:
        print(f"✗ Sprint 3 setup failed: {e}")
    print()

    print("SPRINT 4: Learning & Observability")
    print("-" * 70)
    try:
        from app.modules.imports.application.scoring_engine import ScoringEngine

        sprint4_setup.setup_learning_pipeline(ScoringEngine())
        sprint4_setup.setup_observability()
        sprint4_setup.setup_regression_dataset()
        print("✓ Sprint 4 setup completed successfully")
    except Exception as e:
        print(f"✗ Sprint 4 setup failed: {e}")
    print()

    print("=" * 70)
    print("ALL SPRINTS COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    run_all_sprints()
