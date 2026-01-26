"""Feedback service for tracking classification corrections and model improvement."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class FeedbackEntry:
    """Registro de feedback de clasificación."""

    id: str
    tenant_id: str
    created_at: str
    original_parser: str
    original_confidence: float
    original_doc_type: str
    corrected_parser: str | None
    corrected_doc_type: str | None
    was_correct: bool
    headers: list[str]
    filename: str
    file_extension: str
    decision_log_id: str | None


class FeedbackService:
    """Servicio para tracking de feedback y reentrenamiento."""

    def __init__(self, storage_path: str = "data/feedback"):
        self.logger = logging.getLogger("imports.feedback")
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._entries: list[FeedbackEntry] = []
        self._load_entries()

    def record_feedback(
        self,
        tenant_id: str,
        original_parser: str,
        original_confidence: float,
        original_doc_type: str,
        corrected_parser: str | None,
        corrected_doc_type: str | None,
        was_correct: bool,
        headers: list[str],
        filename: str,
        decision_log_id: str | None = None,
    ) -> FeedbackEntry:
        """Registra feedback de una clasificación."""
        file_extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        entry = FeedbackEntry(
            id=str(uuid4()),
            tenant_id=tenant_id,
            created_at=datetime.utcnow().isoformat(),
            original_parser=original_parser,
            original_confidence=original_confidence,
            original_doc_type=original_doc_type,
            corrected_parser=corrected_parser,
            corrected_doc_type=corrected_doc_type,
            was_correct=was_correct,
            headers=headers,
            filename=filename,
            file_extension=file_extension,
            decision_log_id=decision_log_id,
        )

        self._entries.append(entry)
        self._save_entries()

        self.logger.info(
            f"Feedback recorded: id={entry.id}, was_correct={was_correct}, "
            f"original={original_parser}, corrected={corrected_parser}"
        )

        return entry

    def get_accuracy_stats(self, tenant_id: str | None = None) -> dict[str, Any]:
        """Calcula estadísticas de precisión."""
        entries = self._entries
        if tenant_id:
            entries = [e for e in entries if e.tenant_id == tenant_id]

        if not entries:
            return {
                "total_classifications": 0,
                "correct_count": 0,
                "corrected_count": 0,
                "accuracy_rate": 0.0,
                "by_doc_type": {},
                "most_corrected_parsers": [],
            }

        total = len(entries)
        correct = sum(1 for e in entries if e.was_correct)
        corrected = total - correct

        by_doc_type: dict[str, dict[str, int]] = {}
        for entry in entries:
            doc_type = entry.original_doc_type
            if doc_type not in by_doc_type:
                by_doc_type[doc_type] = {"total": 0, "correct": 0, "corrected": 0}
            by_doc_type[doc_type]["total"] += 1
            if entry.was_correct:
                by_doc_type[doc_type]["correct"] += 1
            else:
                by_doc_type[doc_type]["corrected"] += 1

        for doc_type, stats in by_doc_type.items():
            stats["accuracy_rate"] = (
                stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0
            )

        parser_corrections: dict[str, int] = {}
        for entry in entries:
            if not entry.was_correct:
                parser = entry.original_parser
                parser_corrections[parser] = parser_corrections.get(parser, 0) + 1

        most_corrected = sorted(
            [{"parser": k, "corrections": v} for k, v in parser_corrections.items()],
            key=lambda x: x["corrections"],
            reverse=True,
        )[:10]

        return {
            "total_classifications": total,
            "correct_count": correct,
            "corrected_count": corrected,
            "accuracy_rate": correct / total if total > 0 else 0.0,
            "by_doc_type": by_doc_type,
            "most_corrected_parsers": most_corrected,
        }

    def get_training_data(self, min_entries: int = 50) -> list[tuple[list[str], str]]:
        """
        Genera datos de entrenamiento a partir del feedback.

        Returns:
            Lista de (headers, corrected_doc_type) para reentrenar
        """
        corrected_entries = [e for e in self._entries if not e.was_correct and e.corrected_doc_type]

        if len(corrected_entries) < min_entries:
            self.logger.info(
                f"Not enough corrected entries for training: {len(corrected_entries)} < {min_entries}"
            )
            return []

        training_data: list[tuple[list[str], str]] = []
        for entry in corrected_entries:
            if entry.corrected_doc_type:
                training_data.append((entry.headers, entry.corrected_doc_type))

        return training_data

    def export_for_retraining(self) -> dict[str, Any]:
        """Exporta datos para reentrenamiento del modelo."""
        training_data = self.get_training_data(min_entries=0)

        correct_entries = [e for e in self._entries if e.was_correct]
        for entry in correct_entries:
            training_data.append((entry.headers, entry.original_doc_type))

        return {
            "total_entries": len(self._entries),
            "training_samples": len(training_data),
            "data": [
                {"headers": headers, "doc_type": doc_type} for headers, doc_type in training_data
            ],
            "stats": self.get_accuracy_stats(),
            "exported_at": datetime.utcnow().isoformat(),
        }

    def _get_storage_file(self) -> Path:
        """Get the path to the storage file."""
        return self.storage_path / "feedback_entries.json"

    def _load_entries(self) -> None:
        """Carga entries desde almacenamiento."""
        storage_file = self._get_storage_file()
        if not storage_file.exists():
            self._entries = []
            return

        try:
            with open(storage_file, encoding="utf-8") as f:
                data = json.load(f)
                self._entries = [FeedbackEntry(**entry) for entry in data]
            self.logger.info(f"Loaded {len(self._entries)} feedback entries")
        except Exception as e:
            self.logger.warning(f"Failed to load feedback entries: {e}")
            self._entries = []

    def _save_entries(self) -> None:
        """Persiste entries."""
        storage_file = self._get_storage_file()
        try:
            with open(storage_file, "w", encoding="utf-8") as f:
                json.dump([asdict(e) for e in self._entries], f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save feedback entries: {e}")


feedback_service = FeedbackService()
