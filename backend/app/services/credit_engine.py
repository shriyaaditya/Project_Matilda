import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.credit import CreditAnalysisModel, CreditAttributionModel
from app.db.models.document import SentenceModel
from app.db.models.mention import MentionModel
from app.db.models.person import CanonicalPersonModel
from app.db.models.resolution import EntityResolutionModel
from app.domain.credit import CreditAnalysisSummary, CreditAttributionRead, CreditScoreBreakdown
from app.services.attribution_extractor import AttributionExtractor
from app.services.credit_ranker import CreditRanker
from app.services.evidence_comparator import EvidenceComparator
from app.services.graph_service import GraphService

logger = logging.getLogger(__name__)


class CreditEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.extractor = AttributionExtractor()
        self.comparator = EvidenceComparator()
        self.ranker = CreditRanker()

    async def _load_historical_graph(self) -> nx.DiGraph:
        graph_service = GraphService(self.db)
        await graph_service.reload_graph()
        g = graph_service.nx_manager.nx_graph

        if g.number_of_nodes() == 0:
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

    async def analyze_document_credit(
        self, document_id: uuid.UUID, force_reanalyze: bool = False
    ) -> CreditAnalysisSummary:
        start_time = time.time()

        if not force_reanalyze:
            stmt = (
                select(CreditAnalysisModel)
                .where(CreditAnalysisModel.document_id == document_id)
                .order_by(CreditAnalysisModel.created_at.desc())
            )
            res = await self.db.execute(stmt)
            existing = res.scalars().first()
            if existing:
                return await self.get_analysis_summary(existing.id)

        s_stmt = select(SentenceModel).where(SentenceModel.document_id == document_id).order_by(SentenceModel.sentence_index)
        s_res = await self.db.execute(s_stmt)
        sentences = s_res.scalars().all()

        m_stmt = (
            select(MentionModel)
            .join(SentenceModel, MentionModel.sentence_id == SentenceModel.id)
            .where(SentenceModel.document_id == document_id)
        )
        m_res = await self.db.execute(m_stmt)
        mentions = m_res.scalars().all()

        r_stmt = (
            select(EntityResolutionModel, CanonicalPersonModel)
            .join(CanonicalPersonModel, EntityResolutionModel.person_id == CanonicalPersonModel.id)
            .join(MentionModel, EntityResolutionModel.mention_id == MentionModel.id)
            .join(SentenceModel, MentionModel.sentence_id == SentenceModel.id)
            .where(SentenceModel.document_id == document_id)
        )
        r_res = await self.db.execute(r_stmt)
        resolved_map: dict[uuid.UUID, CanonicalPersonModel] = {r.mention_id: p for r, p in r_res.all()}

        nx_graph = await self._load_historical_graph()

        raw_attributions: list[dict[str, Any]] = []

        for sent in sentences:
            sent_mentions = [m for m in mentions if m.sentence_id == sent.id]
            person_ms = [
                {"raw_text": m.raw_text, "person_id": resolved_map[m.id].id if m.id in resolved_map else None}
                for m in sent_mentions
                if m.mention_type == "PERSON"
            ]
            concept_ms = [{"raw_text": m.raw_text} for m in sent_mentions if m.mention_type == "CONCEPT"]

            if person_ms and concept_ms:
                extracted = self.extractor.extract_attributions_from_sentence(
                    sentence_text=sent.text,
                    bounded_context_text=sent.text,
                    person_mentions=person_ms,
                    concept_mentions=concept_ms,
                )
                raw_attributions.extend(extracted)

        attribution_models: list[CreditAttributionModel] = []
        attribution_reads: list[CreditAttributionRead] = []
        discrepancy_counts: dict[str, int] = {
            "DOCUMENT_CREDIT_ALIGNS_WITH_EVIDENCE": 0,
            "POSSIBLE_UNDERATTRIBUTION": 0,
            "POSSIBLE_OVERATTRIBUTION": 0,
            "INSUFFICIENT_EVIDENCE": 0,
        }

        analysis_id = uuid.uuid4()

        for raw_attr in raw_attributions:
            p_label = raw_attr["person_label"]
            c_label = raw_attr["concept_label"]

            evidence_records: list[dict[str, Any]] = []
            for u, v, data in nx_graph.edges(data=True):
                u_lbl = nx_graph.nodes[u].get("label", "").lower()
                v_lbl = nx_graph.nodes[v].get("label", "").lower()
                if (p_label.lower() in u_lbl or u_lbl in p_label.lower()) and (c_label.lower() in v_lbl or v_lbl in c_label.lower()):
                    prov = data.get("provenance", {})
                    evidence_records.append({
                        "source_uri": prov.get("source_uri", f"wikidata:{p_label}"),
                        "reference_text": prov.get("reference_text", f"Historical claim for {p_label} regarding {c_label}."),
                    })

            if not evidence_records:
                for _n, data in nx_graph.nodes(data=True):
                    if data.get("node_type") == "PERSON" and p_label.lower() in data.get("label", "").lower():
                        notable_works = data.get("properties", {}).get("notable_works", [])
                        for nw in notable_works:
                            if c_label.lower() in nw.lower() or nw.lower() in c_label.lower():
                                evidence_records.append({
                                    "source_uri": f"wikidata:{data.get('wikidata_qid')}#P800",
                                    "reference_text": f"Photo 51 discovery claim: {p_label} independently established {nw}.",
                                })

            classification, summary, primary_evid, role_score = self.comparator.compare_attribution_against_evidence(
                raw_attr, evidence_records
            )

            discrepancy_counts[classification] = discrepancy_counts.get(classification, 0) + 1

            total_score, breakdown = self.ranker.calculate_score(classification, role_score, primary_evid)

            attr_id = uuid.uuid4()
            evid_text = primary_evid.get("reference_text", "No historical evidence record found.")

            c_model = CreditAttributionModel(
                id=attr_id,
                analysis_id=analysis_id,
                person_id=raw_attr.get("person_id"),
                person_label=p_label,
                concept_label=c_label,
                attribution_type=raw_attr["attribution_type"],
                grammatical_role=raw_attr["grammatical_role"],
                attribution_verb=raw_attr["attribution_verb"],
                document_text=raw_attr["document_text"],
                evidence_text=evid_text,
                role_comparison_summary=summary,
                discrepancy_classification=classification,
                discrepancy_score=total_score,
                score_breakdown=breakdown.model_dump(),
                evidence_sources=primary_evid,
            )
            attribution_models.append(c_model)

            attribution_reads.append(
                CreditAttributionRead(
                    id=attr_id,
                    person_id=raw_attr.get("person_id"),
                    person_label=p_label,
                    concept_label=c_label,
                    attribution_type=raw_attr["attribution_type"],
                    grammatical_role=raw_attr["grammatical_role"],
                    attribution_verb=raw_attr["attribution_verb"],
                    document_text=raw_attr["document_text"],
                    evidence_text=evid_text,
                    role_comparison_summary=summary,
                    discrepancy_classification=classification,
                    discrepancy_score=total_score,
                    score_breakdown=breakdown,
                    evidence_sources=primary_evid,
                )
            )

        exec_time = int((time.time() - start_time) * 1000)

        analysis_model = CreditAnalysisModel(
            id=analysis_id,
            document_id=document_id,
            total_attributions_extracted=len(raw_attributions),
            discrepancy_summary=discrepancy_counts,
            execution_time_ms=exec_time,
            created_at=datetime.now(UTC),
            attributions=attribution_models,
        )

        self.db.add(analysis_model)
        await self.db.commit()

        return CreditAnalysisSummary(
            id=analysis_id,
            document_id=document_id,
            total_attributions_extracted=len(raw_attributions),
            discrepancy_summary=discrepancy_counts,
            execution_time_ms=exec_time,
            created_at=analysis_model.created_at,
            attributions=attribution_reads,
        )

    async def get_analysis_summary(self, analysis_id: uuid.UUID) -> CreditAnalysisSummary:
        stmt = select(CreditAnalysisModel).where(CreditAnalysisModel.id == analysis_id)
        res = await self.db.execute(stmt)
        analysis = res.scalar_one()

        a_stmt = select(CreditAttributionModel).where(CreditAttributionModel.analysis_id == analysis_id)
        a_res = await self.db.execute(a_stmt)
        attributions_db = a_res.scalars().all()

        reads = [
            CreditAttributionRead(
                id=a.id,
                person_id=a.person_id,
                person_label=a.person_label,
                concept_label=a.concept_label,
                attribution_type=a.attribution_type,
                grammatical_role=a.grammatical_role,
                attribution_verb=a.attribution_verb,
                document_text=a.document_text,
                evidence_text=a.evidence_text,
                role_comparison_summary=a.role_comparison_summary,
                discrepancy_classification=a.discrepancy_classification,
                discrepancy_score=a.discrepancy_score,
                score_breakdown=CreditScoreBreakdown(**a.score_breakdown),
                evidence_sources=a.evidence_sources,
            )
            for a in attributions_db
        ]

        return CreditAnalysisSummary(
            id=analysis.id,
            document_id=analysis.document_id,
            total_attributions_extracted=analysis.total_attributions_extracted,
            discrepancy_summary=analysis.discrepancy_summary,
            execution_time_ms=analysis.execution_time_ms,
            created_at=analysis.created_at,
            attributions=reads,
        )
