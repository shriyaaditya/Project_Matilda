import logging

from app.domain.unified import UnifiedEvalMetrics

logger = logging.getLogger(__name__)


class UnifiedEvaluationHook:
    """
    Computes benchmark evaluation metrics across Phase 5 omissions and Phase 6 credit findings.
    """

    @staticmethod
    def evaluate_unified_findings(
        pred_omissions: list[str],
        gt_omissions: list[str],
        pred_credits: list[str],
        gt_credits: list[str],
    ) -> UnifiedEvalMetrics:
        def compute_p_r_f1(pred: list[str], gt: list[str]) -> tuple[float, float, float]:
            p_set = set(p.strip().lower() for p in pred if p)
            g_set = set(g.strip().lower() for g in gt if g)

            tp = len(p_set.intersection(g_set))
            precision = (tp / len(p_set)) if p_set else 0.0
            recall = (tp / len(g_set)) if g_set else 0.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
            return round(precision, 4), round(recall, 4), round(f1, 4)

        o_p, o_r, o_f1 = compute_p_r_f1(pred_omissions, gt_omissions)
        c_p, c_r, c_f1 = compute_p_r_f1(pred_credits, gt_credits)

        total_eval = max(1, len(gt_omissions) + len(gt_credits))
        matched_eval = len(set(pred_omissions).intersection(set(gt_omissions))) + len(set(pred_credits).intersection(set(gt_credits)))
        overall_cov = round(matched_eval / total_eval, 4)

        return UnifiedEvalMetrics(
            omission_precision=o_p,
            omission_recall=o_r,
            omission_f1=o_f1,
            credit_precision=c_p,
            credit_recall=c_r,
            credit_f1=c_f1,
            overall_evidence_coverage=overall_cov,
        )
