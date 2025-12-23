"""Tests for decision logger module."""

import pytest

from app.modules.imports.services.decision_logger import (
    DecisionEntry,
    DecisionLog,
    DecisionLogger,
    DecisionStep,
    StepTimer,
)


class TestDecisionStep:
    """Test DecisionStep enum."""

    def test_step_values(self):
        """Verify all expected step values exist."""
        assert DecisionStep.EXTENSION_CHECK == "extension_check"
        assert DecisionStep.HEADER_EXTRACTION == "header_extraction"
        assert DecisionStep.HEURISTIC_CLASSIFICATION == "heuristic_classification"
        assert DecisionStep.ML_CLASSIFICATION == "ml_classification"
        assert DecisionStep.AI_ENHANCEMENT == "ai_enhancement"
        assert DecisionStep.FINAL_DECISION == "final_decision"


class TestDecisionEntry:
    """Test DecisionEntry dataclass."""

    def test_to_dict(self):
        """Test serialization to dict."""
        from datetime import datetime

        entry = DecisionEntry(
            step=DecisionStep.EXTENSION_CHECK,
            timestamp=datetime(2024, 6, 1, 10, 30, 0),
            input_data={"filename": "test.xlsx"},
            output_data={"extension": ".xlsx"},
            confidence=0.95,
            duration_ms=5.2,
        )

        result = entry.to_dict()

        assert result["step"] == "extension_check"
        assert "2024-06-01" in result["timestamp"]
        assert result["input_data"] == {"filename": "test.xlsx"}
        assert result["output_data"] == {"extension": ".xlsx"}
        assert result["confidence"] == 0.95
        assert result["duration_ms"] == 5.2
        assert result["error"] is None

    def test_to_dict_with_error(self):
        """Test serialization with error."""
        from datetime import datetime

        entry = DecisionEntry(
            step=DecisionStep.AI_ENHANCEMENT,
            timestamp=datetime.utcnow(),
            input_data={},
            output_data={},
            error="API timeout",
        )

        result = entry.to_dict()
        assert result["error"] == "API timeout"


class TestDecisionLog:
    """Test DecisionLog dataclass."""

    def test_create_log(self):
        """Test log creation with defaults."""
        log = DecisionLog(
            tenant_id="tenant-123",
            filename="products.xlsx",
        )

        assert log.id is not None
        assert log.tenant_id == "tenant-123"
        assert log.filename == "products.xlsx"
        assert log.entries == []
        assert log.final_parser is None

    def test_add_step(self):
        """Test adding steps to log."""
        log = DecisionLog()

        entry = log.add_step(
            step=DecisionStep.EXTENSION_CHECK,
            input_data={"filename": "test.csv"},
            output_data={"extension": ".csv"},
            confidence=1.0,
            duration_ms=1.5,
        )

        assert len(log.entries) == 1
        assert entry.step == DecisionStep.EXTENSION_CHECK
        assert entry.confidence == 1.0

    def test_to_dict(self):
        """Test full serialization."""
        log = DecisionLog(
            tenant_id="t-1",
            filename="data.xlsx",
        )
        log.add_step(
            step=DecisionStep.EXTENSION_CHECK,
            input_data={"filename": "data.xlsx"},
            output_data={"extension": ".xlsx"},
        )
        log.final_parser = "products_excel"
        log.final_confidence = 0.85

        result = log.to_dict()

        assert result["tenant_id"] == "t-1"
        assert result["filename"] == "data.xlsx"
        assert len(result["entries"]) == 1
        assert result["final_parser"] == "products_excel"
        assert result["final_confidence"] == 0.85

    def test_get_explanation(self):
        """Test human-readable explanation."""
        log = DecisionLog(filename="test.xlsx")
        log.add_step(
            step=DecisionStep.EXTENSION_CHECK,
            input_data={"filename": "test.xlsx"},
            output_data={"extension": ".xlsx"},
        )
        log.add_step(
            step=DecisionStep.HEURISTIC_CLASSIFICATION,
            input_data={},
            output_data={"parser": "products_excel", "reason": "Detected products"},
            confidence=0.8,
        )
        log.final_parser = "products_excel"
        log.final_confidence = 0.8

        explanation = log.get_explanation()

        assert "test.xlsx" in explanation
        assert "Extension Check" in explanation
        assert "Heuristic Classification" in explanation
        assert "products_excel" in explanation
        assert "80%" in explanation


class TestDecisionLogger:
    """Test DecisionLogger service."""

    def test_create_and_get_log(self):
        """Test creating and retrieving logs."""
        logger = DecisionLogger()

        log = logger.create_log(tenant_id="t-1", filename="test.csv")

        retrieved = logger.get_log(log.id)
        assert retrieved is not None
        assert retrieved.id == log.id

    def test_save_log(self):
        """Test saving log updates."""
        logger = DecisionLogger()
        log = logger.create_log(filename="test.xlsx")

        log.final_parser = "generic_excel"
        log.final_confidence = 0.6
        logger.save_log(log)

        retrieved = logger.get_log(log.id)
        assert retrieved.final_parser == "generic_excel"

    def test_record_user_override(self):
        """Test recording user parser override."""
        logger = DecisionLogger()
        log = logger.create_log()
        log.final_parser = "csv_invoices"
        logger.save_log(log)

        logger.record_user_override(log.id, "csv_bank")

        retrieved = logger.get_log(log.id)
        assert retrieved.user_override == "csv_bank"

    def test_get_recent_logs(self):
        """Test listing recent logs."""
        logger = DecisionLogger()

        for i in range(5):
            log = logger.create_log(tenant_id="t-1", filename=f"file{i}.csv")
            logger.save_log(log)

        recent = logger.get_recent_logs(tenant_id="t-1", limit=3)
        assert len(recent) == 3

    def test_get_recent_logs_filter_by_tenant(self):
        """Test filtering logs by tenant."""
        logger = DecisionLogger()

        logger.save_log(logger.create_log(tenant_id="t-1"))
        logger.save_log(logger.create_log(tenant_id="t-2"))
        logger.save_log(logger.create_log(tenant_id="t-1"))

        t1_logs = logger.get_recent_logs(tenant_id="t-1")
        assert len(t1_logs) == 2


class TestStepTimer:
    """Test StepTimer context manager."""

    def test_measures_duration(self):
        """Test that timer measures duration."""
        import time

        with StepTimer() as timer:
            time.sleep(0.01)

        assert timer.duration_ms >= 10
        assert timer.duration_ms < 100

    def test_zero_duration_fast_op(self):
        """Test very fast operations."""
        with StepTimer() as timer:
            _ = 1 + 1

        assert timer.duration_ms >= 0
