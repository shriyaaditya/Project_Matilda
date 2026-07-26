import logging

from app.domain.credit import CreditEvalMetrics

logger = logging.getLogger(__name__)


class CreditEvaluationHook:
    """
    Computes benchmark evaluation metrics (Precision, Recall, F1, FPR) for credit discrepancy detection.
    """

    @staticmethod
    def evaluate_credit_discrepancies(
        predicted_underattributions: list[str],
        ground_truth_underattributions: list[str],
        total_negative_pool: int = 100,
    ) -> CreditEvalMetrics:
        pred_set = set(p.strip().lower() for p in predicted_underattributions if p)
        gt_set = set(g.strip().lower() for g in ground_truth_underattributions if g)

        true_positives = len(pred_set.intersection(gt_set))
        false_positives = len(pred_set - gt_set)
        false_negatives = len(gt_set - pred_set)

        precision = (true_positives / len(pred_set)) if pred_set else 0.0
        recall = (true_positives / len(gt_set)) if gt_set else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        denom_fpr = max(1, total_negative_pool)
        fpr = round(false_positives / denom_fpr, 4)

        return CreditEvalMetrics(
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            false_positive_rate=fpr,
            total_attributions_evaluated=len(pred_set),
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
        )
