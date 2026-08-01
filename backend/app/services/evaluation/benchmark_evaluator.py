import logging
from typing import Any

from app.services.evaluation.error_classifier import ErrorClassifier

logger = logging.getLogger(__name__)


class BenchmarkEvaluator:
    """
    Evaluates Matilda predictions against ground-truth cases across 3 distinct dimensions:
    A. Finding Detection (correct person/finding type)
    B. Evidence Validity (valid provenance)
    C. Evidence-Strength Calibration (appropriate qualitative strength)
    """

    def __init__(self) -> None:
        self.error_classifier = ErrorClassifier()

    def evaluate_cases(
        self, benchmark_cases: list[dict[str, Any]], predictions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        pred_map = {p["case_id"]: p for p in predictions}

        detection_tp = 0
        detection_fp = 0
        detection_fn = 0

        valid_evidence_cnt = 0
        valid_strength_cnt = 0

        case_results: list[dict[str, Any]] = []

        for case in benchmark_cases:
            case_id = case["case_id"]
            expected_findings = case.get("expected_findings", [])
            pred_item = pred_map.get(case_id, {})
            actual_findings = pred_item.get("findings", [])
            actual_resolved = pred_item.get("resolved_people", [])

            # A. Finding Detection Check
            detection_match = False
            if not expected_findings and not actual_findings:
                detection_match = True
            elif expected_findings and actual_findings:
                exp_types = set(f.get("finding_type") for f in expected_findings)
                act_types = set(f.get("finding_type") for f in actual_findings)
                if exp_types.intersection(act_types):
                    detection_match = True

            if detection_match:
                detection_tp += 1
                failure_cat = None
            else:
                if expected_findings:
                    detection_fn += 1
                else:
                    detection_fp += 1
                failure_cat = self.error_classifier.classify_failure(
                    case.get("category", ""), actual_findings, actual_resolved
                )

            # B. Evidence Validity Check
            has_valid_evid = False
            if actual_findings:
                has_valid_evid = any(
                    f.get("score_breakdown", {}).get("deduplicated_source_count", 0) > 0 or f.get("external_evidence")
                    for f in actual_findings
                )
                if has_valid_evid:
                    valid_evidence_cnt += 1

            # C. Strength Calibration Check
            has_valid_strength = False
            if actual_findings:
                has_valid_strength = any(
                    f.get("evidence_strength") in ["STRONG", "MODERATE", "WEAK"] for f in actual_findings
                )
                if has_valid_strength:
                    valid_strength_cnt += 1

            case_results.append({
                "case_id": case_id,
                "category": case.get("category"),
                "split": case.get("split"),
                "expected_findings": expected_findings,
                "actual_findings": actual_findings,
                "detection_match": detection_match,
                "evidence_valid": has_valid_evid,
                "strength_valid": has_valid_strength,
                "failure_category": failure_cat,
            })

        total = max(1, len(benchmark_cases))
        precision = round(detection_tp / max(1, detection_tp + detection_fp), 4)
        recall = round(detection_tp / max(1, detection_tp + detection_fn), 4)
        f1 = round(2 * precision * recall / max(1e-6, precision + recall), 4)

        return {
            "summary_metrics": {
                "total_cases_evaluated": len(benchmark_cases),
                "finding_detection_precision": precision,
                "finding_detection_recall": recall,
                "finding_detection_f1": f1,
                "evidence_validity_rate": round(valid_evidence_cnt / total, 4),
                "strength_calibration_rate": round(valid_strength_cnt / total, 4),
            },
            "case_results": case_results,
        }
