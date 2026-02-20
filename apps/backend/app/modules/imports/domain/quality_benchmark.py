"""
Quality benchmark system for CI/CD gating.
Blocks deployment if accuracy drops or error-rate increases.
"""

from dataclasses import dataclass
from enum import Enum


class BenchmarkStatus(str, Enum):
    """Benchmark evaluation status."""

    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


@dataclass
class BenchmarkThresholds:
    """Thresholds for quality benchmarks."""

    # Minimum acceptable accuracy (%)
    min_parser_accuracy: float = 90.0  # >= 90%
    min_doc_type_accuracy: float = 88.0  # >= 88%
    min_mapping_accuracy: float = 85.0  # >= 85%
    min_validation_pass_rate: float = 95.0  # >= 95%
    min_promotion_success_rate: float = 90.0  # >= 90%

    # Maximum acceptable correction rate (%)
    max_manual_correction_rate: float = 10.0  # <= 10% need correction

    # Error rate (absolute)
    max_error_count_per_batch: int = 100  # <= 100 errors

    # Minimum sample size for meaningful metrics
    min_sample_size: int = 50  # Need at least 50 samples

    # Regression thresholds (percentage points)
    max_regression_threshold: float = 5.0  # If drops >5%, it's concerning


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test."""

    metric_name: str
    current_value: float
    threshold: float
    status: BenchmarkStatus
    message: str
    previous_value: float | None = None
    regression: float | None = None  # percentage point change


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""

    timestamp: str
    environment: str  # "staging" | "production"
    results: list[BenchmarkResult]
    overall_status: BenchmarkStatus
    passed_count: int = 0
    warning_count: int = 0
    failed_count: int = 0

    def summary(self) -> str:
        """Get summary message."""
        status_icon = {
            BenchmarkStatus.PASSED: "[OK]",
            BenchmarkStatus.WARNING: "[WARN]",
            BenchmarkStatus.FAILED: "[FAIL]",
        }

        lines = [
            f"Benchmark Report ({self.environment})",
            f"Overall Status: {status_icon.get(self.overall_status, '?')} {self.overall_status.value}",
            f"Passed: {self.passed_count}, Warnings: {self.warning_count}, Failed: {self.failed_count}",
            "",
        ]

        for result in self.results:
            icon = status_icon.get(result.status, "?")
            regression_str = ""
            if result.regression is not None:
                regression_str = f" (was {result.previous_value:.1f}%, {result.regression:+.1f}pp)"
            lines.append(
                f"{icon} {result.metric_name}: {result.current_value:.1f}% (threshold: {result.threshold:.1f}%){regression_str}"
            )

        return "\n".join(lines)


class QualityBenchmark:
    """
    Benchmark system for quality gating.
    Used in CI/CD pipeline to block bad deployments.
    """

    def __init__(self, thresholds: BenchmarkThresholds | None = None):
        self.thresholds = thresholds or BenchmarkThresholds()
        self.previous_results = {}  # For tracking regression

    def evaluate(
        self,
        metrics: dict[str, float],
        sample_sizes: dict[str, int],
        environment: str = "staging",
    ) -> BenchmarkReport:
        """
        Evaluate metrics against benchmarks.

        Args:
            metrics: {metric_name: value (as %)}, e.g., {"parser_accuracy": 92.5}
            sample_sizes: {metric_name: sample_count}
            environment: "staging" or "production"

        Returns:
            BenchmarkReport with pass/fail status
        """
        from datetime import datetime

        results = []

        # Parser accuracy
        parser_acc = metrics.get("parser_accuracy", 0.0)
        result = self._evaluate_metric(
            "Parser Accuracy",
            parser_acc,
            self.thresholds.min_parser_accuracy,
            sample_sizes.get("parser_accuracy", 0),
        )
        results.append(result)

        # Doc type accuracy
        doc_type_acc = metrics.get("doc_type_accuracy", 0.0)
        result = self._evaluate_metric(
            "Doc Type Classification Accuracy",
            doc_type_acc,
            self.thresholds.min_doc_type_accuracy,
            sample_sizes.get("doc_type_accuracy", 0),
        )
        results.append(result)

        # Mapping accuracy
        mapping_acc = metrics.get("mapping_accuracy", 0.0)
        result = self._evaluate_metric(
            "Field Mapping Accuracy",
            mapping_acc,
            self.thresholds.min_mapping_accuracy,
            sample_sizes.get("mapping_accuracy", 0),
        )
        results.append(result)

        # Validation pass rate
        val_pass = metrics.get("validation_pass_rate", 0.0)
        result = self._evaluate_metric(
            "Validation Pass Rate",
            val_pass,
            self.thresholds.min_validation_pass_rate,
            sample_sizes.get("validation_pass_rate", 0),
        )
        results.append(result)

        # Manual correction rate (lower is better)
        correction_rate = metrics.get("manual_correction_rate", 0.0)
        result = self._evaluate_metric(
            "Manual Correction Rate (lower is better)",
            100 - correction_rate,  # Invert for scoring
            100 - self.thresholds.max_manual_correction_rate,
            sample_sizes.get("manual_correction_rate", 0),
            inverted=True,
        )
        results.append(result)

        # Promotion success rate
        promo_success = metrics.get("promotion_success_rate", 0.0)
        result = self._evaluate_metric(
            "Promotion Success Rate",
            promo_success,
            self.thresholds.min_promotion_success_rate,
            sample_sizes.get("promotion_success_rate", 0),
        )
        results.append(result)

        # Determine overall status
        failed = [r for r in results if r.status == BenchmarkStatus.FAILED]
        warnings = [r for r in results if r.status == BenchmarkStatus.WARNING]

        if failed:
            overall_status = BenchmarkStatus.FAILED
        elif warnings:
            overall_status = BenchmarkStatus.WARNING
        else:
            overall_status = BenchmarkStatus.PASSED

        # Create report
        report = BenchmarkReport(
            timestamp=datetime.utcnow().isoformat(),
            environment=environment,
            results=results,
            overall_status=overall_status,
            passed_count=len([r for r in results if r.status == BenchmarkStatus.PASSED]),
            warning_count=len(warnings),
            failed_count=len(failed),
        )

        return report

    def _evaluate_metric(
        self,
        name: str,
        current_value: float,
        threshold: float,
        sample_size: int,
        inverted: bool = False,
    ) -> BenchmarkResult:
        """Evaluate single metric."""

        # Check sample size
        if sample_size < self.thresholds.min_sample_size:
            return BenchmarkResult(
                metric_name=name,
                current_value=current_value,
                threshold=threshold,
                status=BenchmarkStatus.WARNING,
                message=f"Insufficient samples ({sample_size} < {self.thresholds.min_sample_size})",
            )

        # Check against threshold
        if inverted:
            # For inverted metrics (lower is better)
            meets_threshold = current_value >= (100 - threshold)
        else:
            # For normal metrics (higher is better)
            meets_threshold = current_value >= threshold

        if meets_threshold:
            status = BenchmarkStatus.PASSED
            message = "OK"
        else:
            # Check if it's a regression from previous
            if name in self.previous_results:
                previous = self.previous_results[name]
                regression = current_value - previous
                if abs(regression) > self.thresholds.max_regression_threshold:
                    status = BenchmarkStatus.FAILED
                    message = f"FAILED: {current_value:.1f}% vs threshold {threshold:.1f}% (was {previous:.1f}%)"
                else:
                    status = BenchmarkStatus.WARNING
                    message = f"Below threshold: {current_value:.1f}% vs {threshold:.1f}%"
            else:
                status = BenchmarkStatus.FAILED
                message = f"FAILED: {current_value:.1f}% vs threshold {threshold:.1f}%"

        # Get previous value if available
        previous_value = self.previous_results.get(name)
        regression = None
        if previous_value is not None:
            regression = current_value - previous_value

        result = BenchmarkResult(
            metric_name=name,
            current_value=current_value,
            threshold=threshold,
            status=status,
            message=message,
            previous_value=previous_value,
            regression=regression,
        )

        # Store for next evaluation
        self.previous_results[name] = current_value

        return result

    def should_block_deployment(self, report: BenchmarkReport) -> bool:
        """Determine if deployment should be blocked."""
        return report.overall_status == BenchmarkStatus.FAILED

    def get_deployment_decision(self, report: BenchmarkReport) -> dict:
        """Get deployment decision and reasoning."""
        decision = "APPROVE" if not self.should_block_deployment(report) else "BLOCK"

        failed_metrics = [r for r in report.results if r.status == BenchmarkStatus.FAILED]
        warning_metrics = [r for r in report.results if r.status == BenchmarkStatus.WARNING]

        reason_lines = [
            f"Decision: {decision}",
            f"Environment: {report.environment}",
            "",
        ]

        if failed_metrics:
            reason_lines.append("FAILED CHECKS:")
            for r in failed_metrics:
                reason_lines.append(
                    f"  - {r.metric_name}: {r.current_value:.1f}% (threshold: {r.threshold:.1f}%)"
                )

        if warning_metrics:
            reason_lines.append("WARNINGS:")
            for r in warning_metrics:
                reason_lines.append(f"  - {r.metric_name}: {r.message}")

        if not failed_metrics and not warning_metrics:
            reason_lines.append("All benchmarks passed!")

        return {
            "decision": decision,
            "reason": "\n".join(reason_lines),
            "can_override": decision == "BLOCK",  # Can override failed, but not critical
        }


# Global benchmark instance
quality_benchmark = QualityBenchmark()
