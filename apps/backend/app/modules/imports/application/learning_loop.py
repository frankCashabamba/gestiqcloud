from datetime import datetime

from app.modules.imports.domain.interfaces import ClassifierStrategy, DocType, LearningStore


class ActiveLearning:
    def __init__(self, learning_store: LearningStore, classifier: ClassifierStrategy):
        self.learning_store = learning_store
        self.classifier = classifier
        self.training_samples = []
        self.last_training_timestamp = None

    def add_training_sample(
        self,
        raw_data: dict,
        correct_doc_type: DocType,
        original_doc_type: DocType | None = None,
        confidence_was: float = 0.0,
    ) -> None:
        self.training_samples.append(
            {
                "raw_data": raw_data,
                "correct_doc_type": correct_doc_type,
                "original_doc_type": original_doc_type,
                "confidence_was": confidence_was,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        if original_doc_type and original_doc_type != correct_doc_type:
            self.learning_store.record_correction(
                batch_id="active_learning",
                item_idx=len(self.training_samples) - 1,
                original_doc_type=original_doc_type,
                corrected_doc_type=correct_doc_type,
                confidence_was=confidence_was,
            )

    def should_retrain(self, min_samples: int = 10) -> bool:
        if len(self.training_samples) < min_samples:
            return False

        misclassifications = self.learning_store.get_misclassification_stats()
        total_corrections = sum(misclassifications.values())

        return total_corrections >= min_samples

    def get_training_stats(self) -> dict:
        return {
            "total_samples": len(self.training_samples),
            "misclassifications": self.learning_store.get_misclassification_stats(),
            "last_training": self.last_training_timestamp,
        }

    def retrain(self) -> dict:
        from app.modules.imports.application.quality_gates import BenchmarkRunner

        if not self.training_samples:
            return {"retrained": False, "reason": "no_training_samples"}

        benchmark = BenchmarkRunner(self.training_samples)
        metrics = benchmark.run(self.classifier)

        self.last_training_timestamp = datetime.utcnow().isoformat()

        return {
            "retrained": True,
            "metrics": {
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1_score": metrics.f1_score,
                "total_samples": metrics.total_samples,
                "correct_classifications": metrics.correct_classifications,
            },
            "timestamp": self.last_training_timestamp,
        }

    def get_improvement_rate(self) -> float:
        if not self.training_samples or len(self.training_samples) < 2:
            return 0.0

        misclassifications = self.learning_store.get_misclassification_stats()
        total_corrections = sum(misclassifications.values())

        if total_corrections == 0:
            return 1.0

        improvement = 1.0 - (total_corrections / len(self.training_samples))
        return max(0.0, min(1.0, improvement))


class IncrementalTrainer:
    def __init__(self):
        self.training_pipeline = {}
        self.weekly_improvements = []

    def schedule_training(self, frequency: str = "weekly") -> None:
        self.training_pipeline["frequency"] = frequency
        self.training_pipeline["scheduled_at"] = datetime.utcnow().isoformat()

    def record_weekly_improvement(self, metric_name: str, improvement: float) -> None:
        self.weekly_improvements.append(
            {
                "metric": metric_name,
                "improvement": improvement,
                "week": datetime.utcnow().isocalendar()[1],
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def get_improvement_trend(self) -> dict:
        if not self.weekly_improvements:
            return {"trend": "no_data"}

        recent_improvements = self.weekly_improvements[-4:]
        avg_improvement = sum(i["improvement"] for i in recent_improvements) / len(
            recent_improvements
        )

        return {
            "recent_improvements": recent_improvements,
            "avg_improvement": avg_improvement,
            "trend": "positive" if avg_improvement > 0.0 else "neutral",
        }

    def generate_training_report(self) -> dict:
        return {
            "pipeline_config": self.training_pipeline,
            "weekly_improvements": self.weekly_improvements,
            "trend_analysis": self.get_improvement_trend(),
        }
