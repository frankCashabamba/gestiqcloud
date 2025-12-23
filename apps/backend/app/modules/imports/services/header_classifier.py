"""ML-based header classifier for import files."""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .header_training_data import DOC_TYPES, KEYWORDS_BY_DOCTYPE, TRAINING_DATA

logger = logging.getLogger("app.imports.header_classifier")

MODEL_PATH = Path(__file__).parent / "header_model.joblib"
VECTORIZER_PATH = Path(__file__).parent / "header_vectorizer.joblib"

PARSER_BY_DOCTYPE: dict[str, dict[str, str]] = {
    "products": {
        "xlsx": "products_excel",
        "xls": "products_excel",
        "csv": "csv_products",
        "xml": "xml_products",
        "default": "products_excel",
    },
    "recipes": {
        "xlsx": "xlsx_recipes",
        "xls": "xlsx_recipes",
        "default": "xlsx_recipes",
    },
    "bank_transactions": {
        "xlsx": "xlsx_bank",
        "xls": "xlsx_bank",
        "csv": "csv_bank",
        "xml": "xml_camt053_bank",
        "default": "csv_bank",
    },
    "invoices": {
        "xlsx": "xlsx_invoices",
        "xls": "xlsx_invoices",
        "csv": "csv_invoices",
        "xml": "xml_invoice",
        "default": "csv_invoices",
    },
    "expenses": {
        "xlsx": "xlsx_expenses",
        "xls": "xlsx_expenses",
        "csv": "xlsx_expenses",
        "default": "xlsx_expenses",
    },
}


@dataclass
class ClassificationResult:
    """Result of header classification."""

    suggested_parser: str
    doc_type: str
    confidence: float
    probabilities: dict[str, float] = field(default_factory=dict)
    method: str = "rules"
    features: dict[str, Any] = field(default_factory=dict)


class HeaderClassifier:
    """ML classifier for file headers to predict document type and parser."""

    def __init__(self):
        self.model = None
        self.vectorizer = None
        self._ml_available = False
        self._load_or_create_model()

    def _load_or_create_model(self) -> None:
        """Load pre-trained model or prepare for rule-based classification."""
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._ml_available = True

            if MODEL_PATH.exists() and VECTORIZER_PATH.exists():
                self._load_model()
            else:
                self._train_initial_model()
        except ImportError:
            logger.info("scikit-learn not available, using rule-based classification")
            self._ml_available = False

    def _train_initial_model(self) -> None:
        """Train initial model with default training data."""
        if not self._ml_available:
            return

        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.feature_extraction.text import TfidfVectorizer

            texts = [" ".join(headers) for headers, _ in TRAINING_DATA]
            labels = [doc_type for _, doc_type in TRAINING_DATA]

            self.vectorizer = TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                lowercase=True,
                max_features=500,
            )
            X = self.vectorizer.fit_transform(texts)

            self.model = RandomForestClassifier(
                n_estimators=50,
                max_depth=10,
                random_state=42,
                class_weight="balanced",
            )
            self.model.fit(X, labels)

            self.save_model()
            logger.info("Initial header classifier model trained and saved")
        except Exception as e:
            logger.warning(f"Failed to train initial model: {e}")
            self._ml_available = False

    def classify(
        self,
        headers: list[str],
        sample_rows: list[list[Any]] | None = None,
        file_extension: str = "",
    ) -> ClassificationResult:
        """
        Classify headers to predict document type and parser.

        Args:
            headers: List of column names
            sample_rows: Optional first rows for additional context
            file_extension: File extension (xlsx, csv, xml) to select specific parser

        Returns:
            ClassificationResult with parser, confidence, probabilities
        """
        features = self.get_features(headers, sample_rows)

        if self._ml_available and self.model is not None:
            result = self._classify_ml(headers, features, file_extension)
        else:
            result = self._classify_rules(headers, features, file_extension)

        result.features = features
        return result

    def _classify_ml(
        self,
        headers: list[str],
        features: dict[str, Any],
        file_extension: str,
    ) -> ClassificationResult:
        """Classify using ML model."""
        try:
            text = " ".join(h.lower() for h in headers)
            X = self.vectorizer.transform([text])

            probas = self.model.predict_proba(X)[0]
            classes = self.model.classes_

            probabilities = {cls: float(prob) for cls, prob in zip(classes, probas)}
            predicted_class = max(probabilities, key=lambda k: probabilities[k])
            confidence = probabilities[predicted_class]

            rule_result = self._classify_rules(headers, features, file_extension)
            if rule_result.confidence > confidence:
                rule_result.method = "rules_override"
                return rule_result

            ext = file_extension.lstrip(".").lower()
            parser_map = PARSER_BY_DOCTYPE.get(predicted_class, {})
            suggested_parser = parser_map.get(ext, parser_map.get("default", "generic_excel"))

            return ClassificationResult(
                suggested_parser=suggested_parser,
                doc_type=predicted_class,
                confidence=confidence,
                probabilities=probabilities,
                method="ml",
            )
        except Exception as e:
            logger.warning(f"ML classification failed: {e}, falling back to rules")
            return self._classify_rules(headers, features, file_extension)

    def _classify_rules(
        self,
        headers: list[str],
        features: dict[str, Any],
        file_extension: str,
    ) -> ClassificationResult:
        """Classify using rule-based approach."""
        scores = features.get("keyword_scores", {})

        if not scores:
            return ClassificationResult(
                suggested_parser="generic_excel",
                doc_type="generic",
                confidence=0.3,
                probabilities={dt: 0.25 for dt in DOC_TYPES},
                method="rules_fallback",
            )

        max_score = max(scores.values()) if scores.values() else 0
        total_score = sum(scores.values()) or 1

        probabilities = {dt: scores.get(dt, 0) / total_score for dt in DOC_TYPES}

        best_type = max(scores, key=lambda k: scores[k]) if scores else "generic"
        confidence = min(0.95, (max_score / (total_score * 0.6)) if max_score > 0 else 0.3)

        if max_score < 2:
            confidence = min(confidence, 0.5)

        ext = file_extension.lstrip(".").lower()
        parser_map = PARSER_BY_DOCTYPE.get(best_type, {})
        suggested_parser = parser_map.get(ext, parser_map.get("default", "generic_excel"))

        return ClassificationResult(
            suggested_parser=suggested_parser,
            doc_type=best_type,
            confidence=confidence,
            probabilities=probabilities,
            method="rules",
        )

    def get_features(
        self,
        headers: list[str],
        sample_rows: list[list[Any]] | None = None,
    ) -> dict[str, Any]:
        """Extract features from headers for classification."""
        normalized = [self._normalize_header(h) for h in headers]

        keyword_scores: dict[str, int] = {}
        for doc_type, keywords in KEYWORDS_BY_DOCTYPE.items():
            score = 0
            for header in normalized:
                for kw in keywords:
                    if kw in header or header in kw:
                        score += 1
                        break
            keyword_scores[doc_type] = score

        numeric_cols = 0
        text_cols = 0
        date_cols = 0

        for header in normalized:
            if any(
                kw in header
                for kw in [
                    "precio",
                    "price",
                    "monto",
                    "amount",
                    "cantidad",
                    "qty",
                    "total",
                    "saldo",
                    "balance",
                    "stock",
                    "importe",
                ]
            ):
                numeric_cols += 1
            elif any(kw in header for kw in ["fecha", "date", "periodo", "period", "vencimiento"]):
                date_cols += 1
            elif any(
                kw in header
                for kw in [
                    "nombre",
                    "name",
                    "descripcion",
                    "description",
                    "concepto",
                    "cliente",
                    "customer",
                ]
            ):
                text_cols += 1

        patterns = {
            "snake_case": sum(1 for h in headers if "_" in h),
            "camelCase": sum(1 for h in headers if re.match(r"^[a-z]+[A-Z]", h)),
            "spanish": sum(
                1
                for h in normalized
                if any(kw in h for kw in ["fecha", "nombre", "precio", "cantidad", "total"])
            ),
            "english": sum(
                1
                for h in normalized
                if any(kw in h for kw in ["date", "name", "price", "quantity", "amount"])
            ),
        }

        return {
            "header_count": len(headers),
            "normalized_headers": normalized,
            "keyword_scores": keyword_scores,
            "numeric_cols": numeric_cols,
            "text_cols": text_cols,
            "date_cols": date_cols,
            "patterns": patterns,
        }

    def _normalize_header(self, header: str) -> str:
        """Normalize header for comparison."""
        h = str(header).lower().strip()
        h = re.sub(r"[^a-z0-9áéíóúñü_]", "_", h)
        h = re.sub(r"_+", "_", h).strip("_")
        return h

    def train(self, training_data: list[tuple[list[str], str]]) -> bool:
        """Train or update the model with new examples."""
        if not self._ml_available:
            logger.warning("Cannot train: scikit-learn not available")
            return False

        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.feature_extraction.text import TfidfVectorizer

            all_data = list(TRAINING_DATA) + list(training_data)
            texts = [" ".join(headers) for headers, _ in all_data]
            labels = [doc_type for _, doc_type in all_data]

            self.vectorizer = TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                lowercase=True,
                max_features=500,
            )
            X = self.vectorizer.fit_transform(texts)

            self.model = RandomForestClassifier(
                n_estimators=50,
                max_depth=10,
                random_state=42,
                class_weight="balanced",
            )
            self.model.fit(X, labels)

            self.save_model()
            logger.info(f"Model retrained with {len(all_data)} examples")
            return True
        except Exception as e:
            logger.error(f"Failed to train model: {e}")
            return False

    def save_model(self, path: str | None = None) -> bool:
        """Persist the model to disk."""
        if not self._ml_available or self.model is None:
            return False

        try:
            import joblib

            model_path = Path(path) if path else MODEL_PATH
            vectorizer_path = model_path.parent / "header_vectorizer.joblib"

            joblib.dump(self.model, model_path)
            joblib.dump(self.vectorizer, vectorizer_path)
            logger.info(f"Model saved to {model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False

    def _load_model(self, path: str | None = None) -> bool:
        """Load persisted model from disk."""
        if not self._ml_available:
            return False

        try:
            import joblib

            model_path = Path(path) if path else MODEL_PATH
            vectorizer_path = model_path.parent / "header_vectorizer.joblib"

            if model_path.exists() and vectorizer_path.exists():
                self.model = joblib.load(model_path)
                self.vectorizer = joblib.load(vectorizer_path)
                logger.info(f"Model loaded from {model_path}")
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
            return False

    def load_model(self, path: str) -> bool:
        """Load model from specified path."""
        return self._load_model(path)

    def retrain_with_feedback(self, min_samples: int = 10) -> tuple[bool, str]:
        """
        Retrain model using feedback data.

        Args:
            min_samples: Minimum number of feedback samples required

        Returns:
            Tuple of (success, message)
        """
        try:
            from .feedback_service import feedback_service

            training_data = feedback_service.get_training_data(min_entries=min_samples)

            if not training_data:
                return False, f"Insufficient feedback data (need at least {min_samples} samples)"

            success = self.train(training_data)

            if success:
                return True, f"Model retrained with {len(training_data)} feedback samples"
            else:
                return False, "Training failed (scikit-learn may not be available)"

        except ImportError:
            return False, "Feedback service not available"
        except Exception as e:
            logger.error(f"Error retraining with feedback: {e}")
            return False, f"Retraining error: {str(e)}"


header_classifier = HeaderClassifier()
