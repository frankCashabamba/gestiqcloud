import hashlib
import json
from typing import Optional

from app.modules.imports.domain.interfaces import (
    AnalyzeResult,
    ClassifierStrategy,
    ConfidenceLevel,
    DocType,
)


class ScoringEngine(ClassifierStrategy):
    def __init__(self):
        self.rules = {}
        self.semantic_signals = {}
        self.ocr_patterns = {}

    def register_rule(self, doc_type: str, rule_func) -> None:
        if doc_type not in self.rules:
            self.rules[doc_type] = []
        self.rules[doc_type].append(rule_func)

    def register_semantic_signal(self, doc_type: str, keywords: list[str], weight: float) -> None:
        if doc_type not in self.semantic_signals:
            self.semantic_signals[doc_type] = []
        self.semantic_signals[doc_type].append({"keywords": keywords, "weight": weight})

    def register_ocr_pattern(self, pattern_name: str, pattern: str, doc_type: str) -> None:
        if pattern_name not in self.ocr_patterns:
            self.ocr_patterns[pattern_name] = []
        self.ocr_patterns[pattern_name].append({"pattern": pattern, "doc_type": doc_type})

    def classify(self, raw_data: dict) -> AnalyzeResult:
        scores = self._compute_scores(raw_data)
        best_doc_type, best_score = self._find_best_match(scores)
        confidence = self._score_to_confidence(best_score)
        fingerprint = self._compute_fingerprint(raw_data)

        return AnalyzeResult(
            doc_type=best_doc_type,
            confidence=confidence,
            confidence_score=best_score,
            raw_data=raw_data,
            errors=[],
            metadata={
                "all_scores": scores,
                "fingerprint": fingerprint,
            },
            fingerprint=fingerprint,
        )

    def _compute_scores(self, raw_data: dict) -> dict[str, float]:
        scores = {doc_type.value: 0.0 for doc_type in DocType}

        for doc_type_str, rule_list in self.rules.items():
            doc_type = self._str_to_doc_type(doc_type_str)
            for rule_func in rule_list:
                try:
                    score = rule_func(raw_data)
                    scores[doc_type.value] += score
                except Exception:
                    pass

        for doc_type_str, signals in self.semantic_signals.items():
            doc_type = self._str_to_doc_type(doc_type_str)
            text = self._extract_text(raw_data)
            text_lower = text.lower()
            for signal in signals:
                for keyword in signal["keywords"]:
                    if keyword.lower() in text_lower:
                        scores[doc_type.value] += signal["weight"]

        return scores

    def _find_best_match(self, scores: dict[str, float]) -> tuple[DocType, float]:
        if not scores or max(scores.values()) == 0:
            return DocType.GENERIC, 0.0

        best_type = max(scores, key=scores.get)
        best_score = min(scores[best_type], 1.0)

        return self._str_to_doc_type(best_type), best_score

    def _score_to_confidence(self, score: float) -> ConfidenceLevel:
        if score >= 0.8:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _compute_fingerprint(self, raw_data: dict) -> str:
        keys = sorted(raw_data.keys())
        fingerprint_input = json.dumps(
            {k: type(raw_data[k]).__name__ for k in keys}, sort_keys=True
        )
        return hashlib.sha256(fingerprint_input.encode()).hexdigest()[:16]

    def _extract_text(self, raw_data: dict) -> str:
        text_parts = []
        for value in raw_data.values():
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, (list, dict)):
                text_parts.append(json.dumps(value, default=str))
            else:
                text_parts.append(str(value))
        return " ".join(text_parts)

    def _str_to_doc_type(self, doc_type_str: str) -> DocType:
        try:
            return DocType(doc_type_str)
        except ValueError:
            return DocType.GENERIC

    def score_with_explanation(self, raw_data: dict) -> dict:
        scores = self._compute_scores(raw_data)
        best_doc_type, best_score = self._find_best_match(scores)
        confidence = self._score_to_confidence(best_score)

        return {
            "doc_type": best_doc_type.value,
            "confidence": confidence.value,
            "confidence_score": best_score,
            "all_scores": scores,
            "explanation": f"Classified as {best_doc_type.value} with {confidence.value} confidence",
        }
