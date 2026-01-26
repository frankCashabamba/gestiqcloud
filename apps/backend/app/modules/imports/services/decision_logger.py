"""Decision logging for import classification pipeline."""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DecisionStep(str, Enum):
    EXTENSION_CHECK = "extension_check"
    HEADER_EXTRACTION = "header_extraction"
    HEURISTIC_CLASSIFICATION = "heuristic_classification"
    ML_CLASSIFICATION = "ml_classification"
    AI_ENHANCEMENT = "ai_enhancement"
    MAPPING_SUGGESTION = "mapping_suggestion"
    FINAL_DECISION = "final_decision"


@dataclass
class DecisionEntry:
    """Una entrada en el log de decisiones."""

    step: DecisionStep
    timestamp: datetime
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    confidence: float | None = None
    duration_ms: float | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializa la entrada a diccionario."""
        return {
            "step": self.step.value,
            "timestamp": self.timestamp.isoformat() + "Z",
            "input_data": self.input_data,
            "output_data": self.output_data,
            "confidence": self.confidence,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


@dataclass
class DecisionLog:
    """Log completo de decisiones para una clasificación."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str | None = None
    file_key: str | None = None
    filename: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    entries: list[DecisionEntry] = field(default_factory=list)
    final_parser: str | None = None
    final_confidence: float | None = None
    user_override: str | None = None

    def add_step(
        self,
        step: DecisionStep,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        confidence: float | None = None,
        duration_ms: float | None = None,
        error: str | None = None,
    ) -> DecisionEntry:
        """Añade un paso al log."""
        entry = DecisionEntry(
            step=step,
            timestamp=datetime.utcnow(),
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            duration_ms=duration_ms,
            error=error,
        )
        self.entries.append(entry)
        return entry

    def to_dict(self) -> dict[str, Any]:
        """Serializa para almacenamiento/API."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "file_key": self.file_key,
            "filename": self.filename,
            "created_at": self.created_at.isoformat() + "Z",
            "entries": [e.to_dict() for e in self.entries],
            "final_parser": self.final_parser,
            "final_confidence": self.final_confidence,
            "user_override": self.user_override,
        }

    def get_explanation(self) -> str:
        """Genera explicación legible de las decisiones."""
        lines = [f"Clasificación de archivo: {self.filename or 'N/A'}"]
        lines.append(f"ID: {self.id}")
        lines.append("")

        for entry in self.entries:
            step_name = entry.step.value.replace("_", " ").title()
            lines.append(f"• {step_name}:")

            if entry.error:
                lines.append(f"  Error: {entry.error}")
            else:
                if entry.confidence is not None:
                    lines.append(f"  Confianza: {entry.confidence:.0%}")
                if entry.duration_ms is not None:
                    lines.append(f"  Duración: {entry.duration_ms:.1f}ms")

                out = entry.output_data
                if "parser" in out:
                    lines.append(f"  Parser sugerido: {out['parser']}")
                if "reason" in out:
                    lines.append(f"  Razón: {out['reason']}")

            lines.append("")

        if self.final_parser:
            lines.append(f"Decisión final: {self.final_parser}")
            if self.final_confidence:
                lines.append(f"Confianza final: {self.final_confidence:.0%}")

        if self.user_override:
            lines.append(f"Usuario eligió: {self.user_override}")

        return "\n".join(lines)


class DecisionLogger:
    """Servicio para logging de decisiones."""

    def __init__(self):
        self.logger = logging.getLogger("imports.decisions")
        self._logs: dict[str, DecisionLog] = {}

    def create_log(
        self,
        tenant_id: str | None = None,
        filename: str | None = None,
        file_key: str | None = None,
    ) -> DecisionLog:
        """Crea un nuevo log de decisiones."""
        log = DecisionLog(
            tenant_id=tenant_id,
            filename=filename,
            file_key=file_key,
        )
        self._logs[log.id] = log
        self.logger.debug(f"Created decision log {log.id} for {filename}")
        return log

    def save_log(self, decision_log: DecisionLog):
        """Persiste el log (futuro: a BD)."""
        self._logs[decision_log.id] = decision_log
        self.logger.info(
            f"Decision log {decision_log.id}: "
            f"file={decision_log.filename}, "
            f"parser={decision_log.final_parser}, "
            f"confidence={decision_log.final_confidence}"
        )

    def get_log(self, log_id: str) -> DecisionLog | None:
        """Recupera un log por ID."""
        return self._logs.get(log_id)

    def record_user_override(self, log_id: str, chosen_parser: str):
        """Registra cuando el usuario elige un parser diferente."""
        log = self._logs.get(log_id)
        if log:
            log.user_override = chosen_parser
            self.logger.info(
                f"User override for {log_id}: " f"was={log.final_parser}, now={chosen_parser}"
            )

    def get_recent_logs(self, tenant_id: str | None = None, limit: int = 100) -> list[DecisionLog]:
        """Lista logs recientes para análisis."""
        logs = list(self._logs.values())
        if tenant_id:
            logs = [lg for lg in logs if lg.tenant_id == tenant_id]
        logs.sort(key=lambda x: x.created_at, reverse=True)
        return logs[:limit]


class StepTimer:
    """Context manager para medir tiempo de un paso."""

    def __init__(self):
        self.start_time: float = 0
        self.duration_ms: float = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.duration_ms = (time.perf_counter() - self.start_time) * 1000


decision_logger = DecisionLogger()
