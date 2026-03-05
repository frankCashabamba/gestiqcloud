import json
from datetime import datetime
from typing import Any

from app.modules.imports.domain.interfaces import DocType, LearningStore


class InMemoryLearningStore(LearningStore):
    def __init__(self):
        self.corrections: list[dict] = []
        self.fingerprints: dict[str, list[dict]] = {}
        self.misclassifications: dict[str, int] = {}

    def record_correction(
        self,
        batch_id: str,
        item_idx: int,
        original_doc_type: DocType,
        corrected_doc_type: DocType,
        confidence_was: float,
    ) -> None:
        self.corrections.append(
            {
                "batch_id": batch_id,
                "item_idx": item_idx,
                "original_doc_type": original_doc_type.value,
                "corrected_doc_type": corrected_doc_type.value,
                "confidence_was": confidence_was,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        key = f"{original_doc_type.value}_to_{corrected_doc_type.value}"
        self.misclassifications[key] = self.misclassifications.get(key, 0) + 1

    def get_misclassification_stats(self) -> dict[str, int]:
        return self.misclassifications.copy()

    def get_fingerprint_dataset(self) -> list[dict[str, Any]]:
        return list(self.fingerprints.values())

    def record_fingerprint(
        self,
        fingerprint: str,
        doc_type: DocType,
        raw_data: dict[str, Any],
    ) -> None:
        if fingerprint not in self.fingerprints:
            self.fingerprints[fingerprint] = []

        self.fingerprints[fingerprint].append(
            {
                "doc_type": doc_type.value,
                "raw_data_keys": list(raw_data.keys()),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def get_corrections_by_batch(self, batch_id: str) -> list[dict]:
        return [c for c in self.corrections if c["batch_id"] == batch_id]

    def get_corrections_by_doc_type(self, doc_type: str) -> list[dict]:
        return [c for c in self.corrections if c["original_doc_type"] == doc_type]


class JsonFilelearningStore(LearningStore):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = {"corrections": [], "fingerprints": {}, "stats": {}}
        self._load()

    def _load(self) -> None:
        try:
            with open(self.file_path) as f:
                self.data = json.load(f)
        except FileNotFoundError:
            self.data = {"corrections": [], "fingerprints": {}, "stats": {}}
        except Exception:
            self.data = {"corrections": [], "fingerprints": {}, "stats": {}}

    def _save(self) -> None:
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception:
            pass

    def record_correction(
        self,
        batch_id: str,
        item_idx: int,
        original_doc_type: DocType,
        corrected_doc_type: DocType,
        confidence_was: float,
    ) -> None:
        self.data["corrections"].append(
            {
                "batch_id": batch_id,
                "item_idx": item_idx,
                "original_doc_type": original_doc_type.value,
                "corrected_doc_type": corrected_doc_type.value,
                "confidence_was": confidence_was,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        key = f"{original_doc_type.value}_to_{corrected_doc_type.value}"
        if "stats" not in self.data:
            self.data["stats"] = {}
        self.data["stats"][key] = self.data["stats"].get(key, 0) + 1

        self._save()

    def get_misclassification_stats(self) -> dict[str, int]:
        return self.data.get("stats", {})

    def get_fingerprint_dataset(self) -> list[dict[str, Any]]:
        fingerprints = self.data.get("fingerprints", {})
        result = []
        for fingerprint, entries in fingerprints.items():
            for entry in entries:
                result.append(entry)
        return result

    def record_fingerprint(
        self,
        fingerprint: str,
        doc_type: DocType,
        raw_data: dict[str, Any],
    ) -> None:
        if "fingerprints" not in self.data:
            self.data["fingerprints"] = {}

        if fingerprint not in self.data["fingerprints"]:
            self.data["fingerprints"][fingerprint] = []

        self.data["fingerprints"][fingerprint].append(
            {
                "doc_type": doc_type.value,
                "raw_data_keys": list(raw_data.keys()),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        self._save()
