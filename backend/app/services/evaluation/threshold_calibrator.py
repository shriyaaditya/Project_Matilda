import logging
from typing import Any

from app.services.evaluation.benchmark_evaluator import BenchmarkEvaluator

logger = logging.getLogger(__name__)


class ThresholdCalibrator:
    """
    Performs systematic parameter sweeps over DEVELOPMENT split cases only.
    Explicitly raises ValueError if holdout cases are supplied.
    """

    def __init__(self) -> None:
        self.evaluator = BenchmarkEvaluator()

    def run_calibration_sweep(
        self, dev_benchmark_cases: list[dict[str, Any]], predictions_fn: Any
    ) -> dict[str, Any]:
        # Guard clause: verify NO holdout cases are present
        holdout_cases = [c for c in dev_benchmark_cases if c.get("split") == "holdout"]
        if holdout_cases:
            raise ValueError(
                f"Calibration security failure: {len(holdout_cases)} holdout cases were passed to ThresholdCalibrator! Calibration is strictly restricted to development split."
            )

        sweep_grid = [
            {"coverage_threshold": 0.50, "omission_threshold": 0.45},
            {"coverage_threshold": 0.60, "omission_threshold": 0.50},
            {"coverage_threshold": 0.70, "omission_threshold": 0.55},
        ]

        results = []
        best_setting = sweep_grid[1]
        best_f1 = 0.0

        for setting in sweep_grid:
            # Predict using test settings
            preds = predictions_fn(dev_benchmark_cases, setting)
            eval_res = self.evaluator.evaluate_cases(dev_benchmark_cases, preds)
            f1 = eval_res["summary_metrics"]["finding_detection_f1"]

            results.append({
                "setting": setting,
                "metrics": eval_res["summary_metrics"],
            })

            if f1 > best_f1:
                best_f1 = f1
                best_setting = setting

        return {
            "calibrated_setting": best_setting,
            "best_f1_score": best_f1,
            "sweep_details": results,
        }
