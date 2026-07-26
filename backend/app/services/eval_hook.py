import logging

from app.domain.omission import EvalMetrics

logger = logging.getLogger(__name__)


class EvaluationHook:
    """
    Provides evaluation metrics calculation for gold-set benchmark comparisons.
    Computes Precision, Recall, F1 score, and False Positive Rate (FPR).
    """

    @staticmethod
    def evaluate_omissions(
        predicted_omission_qids: list[str], ground_truth_omission_qids: list[str], total_negative_pool: int = 100
    ) -> EvalMetrics:
        pred_set = set(q.upper() for q in predicted_omission_qids if q)
        gt_set = set(q.upper() for q in ground_truth_omission_qids if q)

        true_positives = len(pred_set.intersection(gt_set))
        false_positives = len(pred_set - gt_set)
        false_negatives = len(gt_set - pred_set)

        precision = (true_positives / len(pred_set)) if pred_set else 0.0
        recall = (true_positives / len(gt_set)) if gt_set else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        denom_fpr = max(1, total_negative_pool)
        fpr = round(false_positives / denom_fpr, 4)

        return EvalMetrics(
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            false_positive_rate=fpr,
            total_candidates=len(pred_set),
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
        )
