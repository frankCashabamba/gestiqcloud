from dataclasses import dataclass


@dataclass
class QualityMetrics:
    total_samples: int
    correct_classifications: int
    precision: float
    recall: float
    f1_score: float
    timestamp: str


class QualityGate:
    def __init__(self, min_precision: float = 0.85, min_recall: float = 0.80):
        self.min_precision = min_precision
        self.min_recall = min_recall
        self.metrics_history = []

    def evaluate(self, metrics: QualityMetrics) -> tuple[bool, str]:
        if metrics.precision < self.min_precision:
            return False, f"Precision {metrics.precision:.3f} below threshold {self.min_precision}"

        if metrics.recall < self.min_recall:
            return False, f"Recall {metrics.recall:.3f} below threshold {self.min_recall}"

        return True, "Quality gate passed"

    def record_metrics(self, metrics: QualityMetrics) -> None:
        self.metrics_history.append(metrics)

    def get_trend(self) -> dict:
        if not self.metrics_history:
            return {"trend": "no_data"}

        recent = self.metrics_history[-5:]
        precisions = [m.precision for m in recent]
        recalls = [m.recall for m in recent]

        avg_precision = sum(precisions) / len(precisions)
        avg_recall = sum(recalls) / len(recalls)

        return {
            "trend": "improving" if avg_precision > 0.5 else "declining",
            "avg_precision": avg_precision,
            "avg_recall": avg_recall,
        }


class BenchmarkRunner:
    def __init__(self, dataset: list[dict]):
        self.dataset = dataset

    def run(self, classifier) -> QualityMetrics:
        from datetime import datetime

        correct = 0
        total = len(self.dataset)

        for sample in self.dataset:
            raw_data = sample["raw_data"]
            expected_doc_type = sample["expected_doc_type"]

            result = classifier.classify(raw_data)

            if result.doc_type.value == expected_doc_type:
                correct += 1

        precision = correct / total if total > 0 else 0.0
        recall = correct / total if total > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return QualityMetrics(
            total_samples=total,
            correct_classifications=correct,
            precision=precision,
            recall=recall,
            f1_score=f1,
            timestamp=datetime.utcnow().isoformat(),
        )


class CIQualityCheck:
    def __init__(self):
        self.gate = QualityGate()

    def check_before_merge(self, classifier, regression_dataset: list[dict]) -> bool:
        benchmark = BenchmarkRunner(regression_dataset)
        metrics = benchmark.run(classifier)

        self.gate.record_metrics(metrics)
        passed, message = self.gate.evaluate(metrics)

        return {
            "passed": passed,
            "message": message,
            "metrics": {
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1_score": metrics.f1_score,
            },
        }
