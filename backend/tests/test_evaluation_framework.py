import pytest

from app.cli.run_benchmark import mock_predict_cases
from app.services.evaluation.benchmark_evaluator import BenchmarkEvaluator
from app.services.evaluation.error_classifier import ErrorClassifier
from app.services.evaluation.gold_set_loader import GoldSetLoader
from app.services.evaluation.threshold_calibrator import ThresholdCalibrator


def test_gold_set_loader_schema() -> None:
    loader = GoldSetLoader("evaluation/matilda_gold_set.json")
    ds = loader.load_dataset(split="all")
    assert ds["metadata"]["total_cases"] >= 10
    assert len(ds["cases"]) >= 10

    dev_cases = loader.load_dataset(split="development")["cases"]
    holdout_cases = loader.load_dataset(split="holdout")["cases"]
    assert len(dev_cases) + len(holdout_cases) == len(ds["cases"])


def test_holdout_security_protection_fails_if_holdout_passed_to_calibrator() -> None:
    loader = GoldSetLoader("evaluation/matilda_gold_set.json")
    # Load dataset including holdout split cases
    mixed_cases = loader.load_dataset(split="all")["cases"]

    calibrator = ThresholdCalibrator()

    def dummy_predict(c_list: list[dict], s: dict) -> list[dict]:
        return []

    # Calibrator MUST raise ValueError if holdout cases are passed
    with pytest.raises(ValueError, match="Calibration security failure"):
        calibrator.run_calibration_sweep(mixed_cases, dummy_predict)


def test_three_part_evaluation_metrics() -> None:
    evaluator = BenchmarkEvaluator()

    cases = [
        {
            "case_id": "TEST-001",
            "category": "OMISSION_POSITIVE",
            "split": "development",
            "expected_findings": [{"finding_type": "POTENTIAL_OMISSION"}],
        }
    ]

    preds = [
        {
            "case_id": "TEST-001",
            "findings": [
                {
                    "finding_type": "POTENTIAL_OMISSION",
                    "evidence_strength": "STRONG",
                    "score_breakdown": {"deduplicated_source_count": 1},
                }
            ],
            "resolved_people": [],
        }
    ]

    res = evaluator.evaluate_cases(cases, preds)

    # 3-part metric verification
    metrics = res["summary_metrics"]
    assert metrics["finding_detection_precision"] == 1.0
    assert metrics["finding_detection_recall"] == 1.0
    assert metrics["evidence_validity_rate"] == 1.0
    assert metrics["strength_calibration_rate"] == 1.0


def test_error_classifier_stage_attribution() -> None:
    classifier = ErrorClassifier()

    cat1 = classifier.classify_failure("AMBIGUOUS_ENTITY_CASE", [], ["Q123"])
    assert cat1 == "ENTITY_RESOLUTION_ERROR"

    cat2 = classifier.classify_failure("OMISSION_POSITIVE", [], [])
    assert cat2 == "KG_COVERAGE_ERROR"


def test_fair_comparison_kg_only_vs_corrective() -> None:
    loader = GoldSetLoader("evaluation/matilda_gold_set.json")
    cases = loader.load_dataset(split="all")["cases"]

    kg_only_preds = mock_predict_cases(cases, mode="kg-only")
    corrective_preds = mock_predict_cases(cases, mode="corrective")

    evaluator = BenchmarkEvaluator()

    eval_kg = evaluator.evaluate_cases(cases, kg_only_preds)
    eval_corr = evaluator.evaluate_cases(cases, corrective_preds)

    # Both run on identical cases and non-retrieval thresholds
    assert eval_kg["summary_metrics"]["total_cases_evaluated"] == eval_corr["summary_metrics"]["total_cases_evaluated"]
    # Corrective retrieval improves recall on outside-120 cases
    assert eval_corr["summary_metrics"]["finding_detection_f1"] >= eval_kg["summary_metrics"]["finding_detection_f1"]
