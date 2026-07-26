import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import SentenceModel
from app.db.models.mention import MentionModel
from app.db.models.omission import OmissionAnalysisModel, OmissionCandidateModel
from app.db.models.person import CanonicalPersonModel
from app.db.models.resolution import EntityResolutionModel
from app.domain.omission import OmissionAnalysisSummary, OmissionCandidateRead, ScoreBreakdown
from app.services.candidate_ranker import CandidateRanker
from app.services.corrective_retriever import CorrectiveRetriever
from app.services.graph_service import GraphService
from app.services.kg_retriever import KGRetriever

logger = logging.getLogger(__name__)


class OmissionEngine:
    def __init__(
        self,
        db: AsyncSession,
        coverage_threshold: float = 0.60,
        omission_threshold: float = 0.50,
    ) -> None:
        self.db = db
        self.coverage_threshold = coverage_threshold
        self.omission_threshold = omission_threshold
        self.ranker = CandidateRanker()
        self.corrective_retriever = CorrectiveRetriever(db)

    async def _load_nx_graph(self) -> nx.DiGraph:
        graph_service = GraphService(self.db)
        await graph_service.reload_graph()
        g = graph_service.nx_manager.nx_graph

        if g.number_of_nodes() == 0:
            # Fallback to loading generated graph JSON file if database tables are unpopulated
            json_path = Path("app/data/generated_women_stem_graph.json")
            if json_path.is_file():
                with open(json_path, encoding="utf-8") as f:
                    data = json.load(f)
                g = nx.DiGraph()
                nodes_by_label: dict[str, str] = {}
                for n in data.get("nodes", []):
                    nid = n.get("wikidata_qid") or n.get("label")
                    nodes_by_label[n.get("label", "").lower()] = nid
                    g.add_node(
                        nid,
                        node_type=n.get("node_type"),
                        label=n.get("label"),
                        wikidata_qid=n.get("wikidata_qid"),
                        properties=n.get("properties", {}),
                    )
                for e in data.get("edges", []):
                    src_lbl = e.get("source_label", "").lower()
                    tgt_lbl = e.get("target_label", "").lower()
                    src_id = e.get("source_qid") or nodes_by_label.get(src_lbl)
                    tgt_id = e.get("target_qid") or nodes_by_label.get(tgt_lbl)
                    if src_id and tgt_id:
                        g.add_edge(
                            src_id,
                            tgt_id,
                            edge_type=e.get("edge_type"),
                            provenance=e.get("provenance", {}),
                        )

        return g

    async def analyze_document_omissions(
        self, document_id: uuid.UUID, force_reanalyze: bool = False
    ) -> OmissionAnalysisSummary:
        start_time = time.time()

        # Check existing analysis if force_reanalyze is False
        if not force_reanalyze:
            stmt = (
                select(OmissionAnalysisModel)
                .where(OmissionAnalysisModel.document_id == document_id)
                .order_by(OmissionAnalysisModel.created_at.desc())
            )
            res = await self.db.execute(stmt)
            existing = res.scalars().first()
            if existing:
                return await self.get_analysis_summary(existing.id)

        # 1. Fetch Document Concepts (Phase 2 CONCEPT mentions)
        m_stmt = (
            select(MentionModel.raw_text)
            .join(SentenceModel, MentionModel.sentence_id == SentenceModel.id)
            .where(SentenceModel.document_id == document_id, MentionModel.mention_type == "CONCEPT")
        )
        m_res = await self.db.execute(m_stmt)
        doc_concepts_raw = [row[0] for row in m_res.all()]
        doc_concepts = list(set([c.strip() for c in doc_concepts_raw if c and len(c.strip()) >= 3]))

        # Extract fields from concepts or document metadata
        doc_fields = ["STEM"]

        # 2. Fetch Present Person Identities in Document (Phase 3 resolved people)
        r_stmt = (
            select(CanonicalPersonModel.wikidata_qid, CanonicalPersonModel.canonical_name)
            .join(EntityResolutionModel, EntityResolutionModel.person_id == CanonicalPersonModel.id)
            .join(MentionModel, EntityResolutionModel.mention_id == MentionModel.id)
            .join(SentenceModel, MentionModel.sentence_id == SentenceModel.id)
            .where(SentenceModel.document_id == document_id)
        )
        r_res = await self.db.execute(r_stmt)
        present_qids: set[str] = set()
        present_names: set[str] = set()

        for qid, name in r_res.all():
            if qid:
                present_qids.add(qid.strip().upper())
            if name:
                present_names.add(name.strip().lower())

        # 3. Load NetworkX historical graph
        nx_graph = await self._load_nx_graph()

        # 4. KG Retrieval
        kg_retriever = KGRetriever(nx_graph)
        candidates = kg_retriever.find_candidates_for_concepts(doc_concepts, doc_fields)

        # 5. Evaluate Local KG Coverage Score
        matched_concept_candidates_cnt = sum(1 for c in candidates if c.get("has_concept_specific_evidence"))
        doc_concept_cnt = max(1, len(doc_concepts))
        coverage_score = round(min(1.0, matched_concept_candidates_cnt / doc_concept_cnt), 4)

        triggered_corrective = False
        if coverage_score < self.coverage_threshold:
            triggered_corrective = True
            ext_candidates = await self.corrective_retriever.search_external_candidates(doc_concepts)
            # Deduplicate external discoveries with local candidates
            existing_keys = {c.get("wikidata_qid") or c.get("person_label") for c in candidates}
            for ext_c in ext_candidates:
                key = ext_c.get("wikidata_qid") or ext_c.get("person_label")
                if key not in existing_keys:
                    candidates.append(ext_c)

        # 6. Rank Candidates & Classify
        surfaced_candidate_models: list[OmissionCandidateModel] = []
        surfaced_reads: list[OmissionCandidateRead] = []

        analysis_id = uuid.uuid4()

        for cand in candidates:
            p_label = cand["person_label"]
            p_qid = cand.get("wikidata_qid")
            clean_qid = p_qid.strip().upper() if p_qid else None
            clean_name = p_label.strip().lower()
            has_concept_evid = cand.get("has_concept_specific_evidence", False)

            score, breakdown = self.ranker.calculate_score(cand, doc_concept_cnt)

            is_present = (clean_qid and clean_qid in present_qids) or (clean_name in present_names)

            if is_present:
                classification = "PRESENT_RELEVANT_CONTRIBUTOR"
            elif has_concept_evid and score >= self.omission_threshold:
                classification = "POTENTIAL_OMISSION"
            else:
                classification = "INSUFFICIENT_EVIDENCE"

            # Filter out INSUFFICIENT_EVIDENCE candidates from final surfaced results
            if classification in ["POTENTIAL_OMISSION", "PRESENT_RELEVANT_CONTRIBUTOR"]:
                cand_id = uuid.uuid4()
                c_model = OmissionCandidateModel(
                    id=cand_id,
                    analysis_id=analysis_id,
                    person_label=p_label,
                    wikidata_qid=clean_qid,
                    classification=classification,
                    has_concept_specific_evidence=has_concept_evid,
                    relevance_score=score,
                    score_breakdown=breakdown.model_dump(),
                    graph_path=cand.get("graph_paths", []),
                    provenance=cand.get("provenance_records", [{}])[0] if cand.get("provenance_records") else {},
                    is_external_discovery=cand.get("is_external_discovery", False),
                )
                surfaced_candidate_models.append(c_model)

                surfaced_reads.append(
                    OmissionCandidateRead(
                        id=cand_id,
                        person_label=p_label,
                        wikidata_qid=clean_qid,
                        classification=classification,
                        has_concept_specific_evidence=has_concept_evid,
                        relevance_score=score,
                        score_breakdown=breakdown,
                        graph_path=cand.get("graph_paths", []),
                        provenance=cand.get("provenance_records", [{}])[0] if cand.get("provenance_records") else {},
                        is_external_discovery=cand.get("is_external_discovery", False),
                    )
                )

        exec_time = int((time.time() - start_time) * 1000)

        analysis_model = OmissionAnalysisModel(
            id=analysis_id,
            document_id=document_id,
            graph_version="1.0.0",
            coverage_score=coverage_score,
            triggered_corrective_retrieval=triggered_corrective,
            execution_time_ms=exec_time,
            created_at=datetime.now(UTC),
            candidates=surfaced_candidate_models,
        )

        self.db.add(analysis_model)
        await self.db.commit()

        return OmissionAnalysisSummary(
            id=analysis_id,
            document_id=document_id,
            graph_version="1.0.0",
            coverage_score=coverage_score,
            triggered_corrective_retrieval=triggered_corrective,
            execution_time_ms=exec_time,
            created_at=analysis_model.created_at,
            candidates=surfaced_reads,
        )

    async def get_analysis_summary(self, analysis_id: uuid.UUID) -> OmissionAnalysisSummary:
        stmt = select(OmissionAnalysisModel).where(OmissionAnalysisModel.id == analysis_id)
        res = await self.db.execute(stmt)
        analysis = res.scalar_one()

        c_stmt = select(OmissionCandidateModel).where(OmissionCandidateModel.analysis_id == analysis_id)
        c_res = await self.db.execute(c_stmt)
        candidates_db = c_res.scalars().all()

        reads = [
            OmissionCandidateRead(
                id=c.id,
                person_label=c.person_label,
                wikidata_qid=c.wikidata_qid,
                classification=c.classification,
                has_concept_specific_evidence=c.has_concept_specific_evidence,
                relevance_score=c.relevance_score,
                score_breakdown=ScoreBreakdown(**c.score_breakdown),
                graph_path=c.graph_path,
                provenance=c.provenance,
                is_external_discovery=c.is_external_discovery,
            )
            for c in candidates_db
        ]

        return OmissionAnalysisSummary(
            id=analysis.id,
            document_id=analysis.document_id,
            graph_version=analysis.graph_version,
            coverage_score=analysis.coverage_score,
            triggered_corrective_retrieval=analysis.triggered_corrective_retrieval,
            execution_time_ms=analysis.execution_time_ms,
            created_at=analysis.created_at,
            candidates=reads,
        )
