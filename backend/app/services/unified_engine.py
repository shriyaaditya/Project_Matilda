import logging
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.unified import UnifiedAnalysisModel, UnifiedFindingModel
from app.domain.unified import UnifiedAnalysisSummary, UnifiedFindingRead, UnifiedScoreBreakdown
from app.services.credit_engine import CreditEngine
from app.services.evidence_fuser import EvidenceFuser
from app.services.evidence_packet_builder import EvidencePacketBuilder
from app.services.explanation_generator import ExplanationGenerator
from app.services.grounded_explanation_service import GroundedExplanationService
from app.services.llm_reasoner import LLMReasonerService
from app.services.omission_engine import OmissionEngine

logger = logging.getLogger(__name__)


class UnifiedEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.omission_engine = OmissionEngine(db)
        self.credit_engine = CreditEngine(db)
        self.fuser = EvidenceFuser()
        self.explainer = ExplanationGenerator()
        self.llm_reasoner = LLMReasonerService()
        self.grounded_explainer = GroundedExplanationService()

    async def analyze_document_unified(
        self,
        document_id: uuid.UUID,
        force_reanalyze: bool = False,
        reasoning_enabled: bool | None = None,
        explanation_enabled: bool | None = None,
    ) -> UnifiedAnalysisSummary:
        start_time = time.time()

        use_reasoning = settings.LLM_REASONING_ENABLED if reasoning_enabled is None else reasoning_enabled
        use_explanation = settings.LLM_EXPLANATION_ENABLED if explanation_enabled is None else explanation_enabled

        if not force_reanalyze:
            stmt = (
                select(UnifiedAnalysisModel)
                .where(UnifiedAnalysisModel.document_id == document_id)
                .order_by(UnifiedAnalysisModel.created_at.desc())
            )
            res = await self.db.execute(stmt)
            existing = res.scalars().first()
            if existing:
                return await self.get_analysis_summary(existing.id)

        # 1. Fetch Phase 5 Omission Analysis
        omission_summary = await self.omission_engine.analyze_document_omissions(document_id, force_reanalyze=force_reanalyze)

        # 2. Fetch Phase 6 Credit Analysis
        credit_summary = await self.credit_engine.analyze_document_credit(document_id, force_reanalyze=force_reanalyze)

        finding_models: list[UnifiedFindingModel] = []
        finding_reads: list[UnifiedFindingRead] = []

        omission_count = 0
        underattrib_count = 0
        overattrib_count = 0
        aligns_count = 0
        insufficient_count = 0

        analysis_id = uuid.uuid4()

        # 3. Process Phase 5 Omissions
        for cand in omission_summary.candidates:
            if cand.classification == "POTENTIAL_OMISSION":
                raw_evid = cand.provenance if isinstance(cand.provenance, list) else ([cand.provenance] if cand.provenance else [])
                fused_score, strength, breakdown = self.fuser.fuse_evidence(raw_evid, cand.relevance_score)

                final_finding_type = "POTENTIAL_OMISSION"

                # Phase 9 LLM Evidence Reasoning
                if use_reasoning:
                    packet = EvidencePacketBuilder.build_packet(
                        document_id=str(document_id),
                        candidate_id=cand.wikidata_qid or cand.person_label,
                        target_person_name=cand.person_label,
                        target_person_qid=cand.wikidata_qid,
                        sentence_text="Document omission context",
                        page_number=1,
                        paragraph_index=0,
                        document_concepts=["historical STEM concepts"],
                        external_evidence_records=raw_evid,
                        deterministic_phase5_score=cand.relevance_score,
                        deterministic_phase6_finding="POTENTIAL_OMISSION",
                    )
                    reasoning_res = await self.llm_reasoner.execute_reasoning(
                        packet, db_session=self.db, reasoning_enabled=True
                    )
                    final_finding_type = reasoning_res.validated_judgment

                if final_finding_type == "POTENTIAL_OMISSION":
                    omission_count += 1
                elif final_finding_type == "INSUFFICIENT_EVIDENCE":
                    insufficient_count += 1

                finding_dict_for_exp = {
                    "person_label": cand.person_label,
                    "concept_label": "historical STEM concepts",
                    "finding_type": final_finding_type,
                    "evidence_strength": strength,
                    "external_evidence": raw_evid,
                    "wikidata_qid": cand.wikidata_qid,
                }

                explanation = await self.grounded_explainer.generate_explanation(
                    finding_dict_for_exp, explanation_enabled=use_explanation
                )

                f_id = uuid.uuid4()
                f_model = UnifiedFindingModel(
                    id=f_id,
                    analysis_id=analysis_id,
                    originating_phase="PHASE_5_OMISSION",
                    person_id=None,
                    person_label=cand.person_label,
                    wikidata_qid=cand.wikidata_qid,
                    concept_label="historical STEM concepts",
                    finding_type=final_finding_type,
                    evidence_strength=strength,
                    fused_score=fused_score,
                    explanation_text=explanation,
                    score_breakdown=breakdown.model_dump(),
                    document_provenance={"source": "document_omission_scan"},
                    external_evidence=cand.provenance,
                    graph_paths=cand.graph_path,
                )
                finding_models.append(f_model)

                finding_reads.append(
                    UnifiedFindingRead(
                        id=f_id,
                        originating_phase="PHASE_5_OMISSION",
                        person_id=None,
                        person_label=cand.person_label,
                        wikidata_qid=cand.wikidata_qid,
                        concept_label="historical STEM concepts",
                        finding_type=final_finding_type,
                        evidence_strength=strength,
                        fused_score=fused_score,
                        explanation_text=explanation,
                        score_breakdown=breakdown,
                        document_provenance={"source": "document_omission_scan"},
                        external_evidence=cand.provenance,
                        graph_paths=cand.graph_path,
                    )
                )

        # 4. Process Phase 6 Credit Attributions
        for attr in credit_summary.attributions:
            raw_evid = attr.evidence_sources if isinstance(attr.evidence_sources, list) else ([attr.evidence_sources] if attr.evidence_sources else [])
            fused_score, strength, breakdown = self.fuser.fuse_evidence(raw_evid, attr.discrepancy_score)

            final_finding_type = attr.discrepancy_classification

            # Phase 9 LLM Evidence Reasoning
            if use_reasoning:
                packet = EvidencePacketBuilder.build_packet(
                    document_id=str(document_id),
                    candidate_id=f"credit-{attr.person_id or attr.person_label}",
                    target_person_name=attr.person_label,
                    target_person_qid=None,
                    sentence_text=attr.document_text,
                    page_number=1,
                    paragraph_index=0,
                    document_concepts=[attr.concept_label],
                    external_evidence_records=raw_evid,
                    deterministic_phase5_score=0.0,
                    deterministic_phase6_finding=attr.discrepancy_classification,
                )
                reasoning_res = await self.llm_reasoner.execute_reasoning(
                    packet, db_session=self.db, reasoning_enabled=True
                )
                final_finding_type = reasoning_res.validated_judgment

            if final_finding_type == "POSSIBLE_UNDERATTRIBUTION":
                underattrib_count += 1
            elif final_finding_type == "POSSIBLE_OVERATTRIBUTION":
                overattrib_count += 1
            elif final_finding_type in ["DOCUMENT_CREDIT_ALIGNS_WITH_EVIDENCE", "CREDIT_ALIGNS"]:
                aligns_count += 1
            else:
                insufficient_count += 1

            finding_dict_for_exp = {
                "person_label": attr.person_label,
                "concept_label": attr.concept_label,
                "finding_type": final_finding_type,
                "evidence_strength": strength,
                "external_evidence": raw_evid,
            }

            explanation = await self.grounded_explainer.generate_explanation(
                finding_dict_for_exp, explanation_enabled=use_explanation
            )

            f_id = uuid.uuid4()
            f_model = UnifiedFindingModel(
                id=f_id,
                analysis_id=analysis_id,
                originating_phase="PHASE_6_CREDIT",
                person_id=attr.person_id,
                person_label=attr.person_label,
                wikidata_qid=None,
                concept_label=attr.concept_label,
                finding_type=final_finding_type,
                evidence_strength=strength,
                fused_score=fused_score,
                explanation_text=explanation,
                score_breakdown=breakdown.model_dump(),
                document_provenance={"text": attr.document_text},
                external_evidence=attr.evidence_sources,
                graph_paths=[],
            )
            finding_models.append(f_model)

            finding_reads.append(
                UnifiedFindingRead(
                    id=f_id,
                    originating_phase="PHASE_6_CREDIT",
                    person_id=attr.person_id,
                    person_label=attr.person_label,
                    wikidata_qid=None,
                    concept_label=attr.concept_label,
                    finding_type=final_finding_type,
                    evidence_strength=strength,
                    fused_score=fused_score,
                    explanation_text=explanation,
                    score_breakdown=breakdown,
                    document_provenance={"text": attr.document_text},
                    external_evidence=attr.evidence_sources,
                    graph_paths=[],
                )
            )

        # 5. Compute Neutral Descriptive Coverage Indicator
        total_eval_claims = aligns_count + omission_count + underattrib_count
        evidence_attention_score = round(aligns_count / total_eval_claims, 4) if total_eval_claims > 0 else 1.0

        exec_time = int((time.time() - start_time) * 1000)

        analysis_model = UnifiedAnalysisModel(
            id=analysis_id,
            document_id=document_id,
            total_findings_count=len(finding_models),
            omission_count=omission_count,
            underattribution_count=underattrib_count,
            overattribution_count=overattrib_count,
            credit_aligns_count=aligns_count,
            insufficient_evidence_count=insufficient_count,
            evidence_attention_score=evidence_attention_score,
            corrective_retrieval_used=omission_summary.triggered_corrective_retrieval,
            execution_time_ms=exec_time,
            created_at=datetime.now(UTC),
            findings=finding_models,
        )

        self.db.add(analysis_model)
        await self.db.commit()

        return UnifiedAnalysisSummary(
            id=analysis_id,
            document_id=document_id,
            total_findings_count=len(finding_models),
            omission_count=omission_count,
            underattribution_count=underattrib_count,
            overattribution_count=overattrib_count,
            credit_aligns_count=aligns_count,
            insufficient_evidence_count=insufficient_count,
            evidence_attention_score=evidence_attention_score,
            corrective_retrieval_used=omission_summary.triggered_corrective_retrieval,
            execution_time_ms=exec_time,
            created_at=analysis_model.created_at,
            findings=finding_reads,
        )

    async def get_analysis_summary(self, analysis_id: uuid.UUID) -> UnifiedAnalysisSummary:
        stmt = select(UnifiedAnalysisModel).where(UnifiedAnalysisModel.id == analysis_id)
        res = await self.db.execute(stmt)
        analysis = res.scalar_one()

        f_stmt = select(UnifiedFindingModel).where(UnifiedFindingModel.analysis_id == analysis_id)
        f_res = await self.db.execute(f_stmt)
        findings_db = f_res.scalars().all()

        reads = [
            UnifiedFindingRead(
                id=f.id,
                originating_phase=f.originating_phase,
                person_id=f.person_id,
                person_label=f.person_label,
                wikidata_qid=f.wikidata_qid,
                concept_label=f.concept_label,
                finding_type=f.finding_type,
                evidence_strength=f.evidence_strength,
                fused_score=f.fused_score,
                explanation_text=f.explanation_text,
                score_breakdown=UnifiedScoreBreakdown(**f.score_breakdown),
                document_provenance=f.document_provenance,
                external_evidence=f.external_evidence,
                graph_paths=f.graph_paths,
            )
            for f in findings_db
        ]

        return UnifiedAnalysisSummary(
            id=analysis.id,
            document_id=analysis.document_id,
            total_findings_count=analysis.total_findings_count,
            omission_count=analysis.omission_count,
            underattribution_count=analysis.underattribution_count,
            overattribution_count=analysis.overattribution_count,
            credit_aligns_count=analysis.credit_aligns_count,
            insufficient_evidence_count=analysis.insufficient_evidence_count,
            evidence_attention_score=analysis.evidence_attention_score,
            corrective_retrieval_used=analysis.corrective_retrieval_used,
            execution_time_ms=analysis.execution_time_ms,
            created_at=analysis.created_at,
            findings=reads,
        )
