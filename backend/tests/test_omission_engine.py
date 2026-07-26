import uuid
from datetime import UTC, datetime

import networkx as nx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import DocumentModel, PageModel, ParagraphModel, SentenceModel
from app.db.models.mention import MentionModel
from app.db.models.person import CanonicalPersonModel
from app.db.models.resolution import EntityResolutionModel
from app.services.candidate_ranker import CandidateRanker
from app.services.eval_hook import EvaluationHook
from app.services.kg_retriever import KGRetriever
from app.services.omission_engine import OmissionEngine


def test_candidate_ranker_concept_evidence_requirement() -> None:
    ranker = CandidateRanker()

    # Candidate A: Direct CONTRIBUTED_TO claim (concept specific evidence)
    cand_a = {
        "person_label": "Emmy Noether",
        "has_concept_specific_evidence": True,
        "matched_concepts": ["Noether's theorem"],
        "relationship_types": ["CONTRIBUTED_TO"],
        "min_distance": 1,
        "provenance_records": [{"source_uri": "wikidata:Q7065#P800", "reference_text": "Symmetry in physics discovery"}],
    }
    score_a, breakdown_a = ranker.calculate_score(cand_a, total_doc_concepts=1)
    assert score_a >= 0.50
    assert breakdown_a.concept_evidence_score > 0.0

    # Candidate B: ASSOCIATED_WITH field match only (context only, no concept evidence)
    cand_b = {
        "person_label": "Marie Curie",
        "has_concept_specific_evidence": False,
        "matched_concepts": [],
        "relationship_types": ["ASSOCIATED_WITH"],
        "min_distance": 2,
        "provenance_records": [{"source_uri": "seed_manifest:Marie Curie", "reference_text": "Field physics"}],
    }
    score_b, breakdown_b = ranker.calculate_score(cand_b, total_doc_concepts=1)
    assert breakdown_b.concept_evidence_score == 0.0
    assert score_b < 0.50


def test_eval_hook_metrics() -> None:
    pred_omissions = ["Q7474", "Q7065", "Q234389"]
    gt_omissions = ["Q7474", "Q7065", "Q11641"]

    metrics = EvaluationHook.evaluate_omissions(pred_omissions, gt_omissions, total_negative_pool=100)
    assert metrics.true_positives == 2
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.precision == pytest.approx(0.6667, abs=1e-3)
    assert metrics.recall == pytest.approx(0.6667, abs=1e-3)
    assert metrics.f1_score == pytest.approx(0.6667, abs=1e-3)


@pytest.mark.asyncio
async def test_kg_retriever_traversal() -> None:
    g = nx.DiGraph()
    g.add_node("p1", node_type="PERSON", label="Emmy Noether", wikidata_qid="Q7065")
    g.add_node("c1", node_type="CONCEPT", label="Noether's theorem")
    g.add_edge("p1", "c1", edge_type="CONTRIBUTED_TO", provenance={"source_uri": "wikidata:Q7065#P800", "reference_text": "Ref"})

    retriever = KGRetriever(g)
    candidates = retriever.find_candidates_for_concepts(["Noether's theorem"], ["Physics"])

    assert len(candidates) == 1
    assert candidates[0]["person_label"] == "Emmy Noether"
    assert candidates[0]["has_concept_specific_evidence"] is True


@pytest.mark.asyncio
async def test_omission_engine_end_to_end(db_session: AsyncSession) -> None:
    # Setup mock document in DB
    doc_id = uuid.uuid4()
    page_id = uuid.uuid4()
    para_id = uuid.uuid4()
    sent_id = uuid.uuid4()
    mention_id = uuid.uuid4()
    person_id = uuid.uuid4()

    doc = DocumentModel(
        id=doc_id,
        filename="symmetry_physics_paper.pdf",
        file_size_bytes=1024,
        sha256_hash=f"hash_{doc_id.hex}",
        file_path="/tmp/test.pdf",
        page_count=1,
        status="PARSED",
        created_at=datetime.now(UTC),
    )
    page = PageModel(id=page_id, document_id=doc_id, page_number=1, has_extractable_text=True, raw_text="Noether's theorem in physics.")
    para = ParagraphModel(id=para_id, page_id=page_id, document_id=doc_id, paragraph_index=0, text="Noether's theorem in physics.")
    sent = SentenceModel(
        id=sent_id,
        paragraph_id=para_id,
        document_id=doc_id,
        page_number=1,
        paragraph_index=0,
        sentence_index=0,
        global_sentence_index=0,
        text="Noether's theorem in physics.",
        char_count=28,
    )
    mention = MentionModel(
        id=mention_id,
        document_id=doc_id,
        sentence_id=sent_id,
        page_number=1,
        paragraph_index=0,
        sentence_index=0,
        mention_type="CONCEPT",
        raw_text="Noether's theorem",
        normalized_text="noether's theorem",
        start_char=0,
        end_char=17,
        extraction_method="spacy_noun_chunks",
        model_version="1.0.0",
    )
    person = CanonicalPersonModel(
        id=person_id,
        canonical_name="Albert Einstein",
        wikidata_qid="Q937",
        created_at=datetime.now(UTC),
    )
    resolution = EntityResolutionModel(
        id=uuid.uuid4(),
        document_id=doc_id,
        mention_id=mention_id,
        person_id=person_id,
        status="RESOLVED",
        resolution_score=0.90,
        matched_qid="Q937",
        evidence={"method": "exact_match"},
        created_at=datetime.now(UTC),
    )

    db_session.add_all([doc, page, para, sent, mention, person, resolution])
    await db_session.commit()

    engine = OmissionEngine(db_session)
    summary = await engine.analyze_document_omissions(doc_id, force_reanalyze=True)

    assert summary.document_id == doc_id
    assert summary.coverage_score >= 0.0
    assert len(summary.candidates) >= 1

    labels = [c.person_label for c in summary.candidates]
    assert "Emmy Noether" in labels

    en_cand = next(c for c in summary.candidates if c.person_label == "Emmy Noether")
    assert en_cand.classification == "POTENTIAL_OMISSION"
    assert en_cand.has_concept_specific_evidence is True
    assert en_cand.relevance_score >= 0.50


@pytest.mark.asyncio
async def test_omission_api_endpoints(async_client: AsyncClient, db_session: AsyncSession) -> None:
    # Setup mock document
    doc_id = uuid.uuid4()
    page_id = uuid.uuid4()
    para_id = uuid.uuid4()
    sent_id = uuid.uuid4()
    mention_id = uuid.uuid4()

    doc = DocumentModel(
        id=doc_id,
        filename="api_test.pdf",
        file_size_bytes=500,
        sha256_hash=f"hash_{doc_id.hex}",
        file_path="/tmp/api.pdf",
        page_count=1,
        status="PARSED",
        created_at=datetime.now(UTC),
    )
    page = PageModel(id=page_id, document_id=doc_id, page_number=1, has_extractable_text=True, raw_text="Noether's theorem discovery.")
    para = ParagraphModel(id=para_id, page_id=page_id, document_id=doc_id, paragraph_index=0, text="Noether's theorem discovery.")
    sent = SentenceModel(
        id=sent_id,
        paragraph_id=para_id,
        document_id=doc_id,
        page_number=1,
        paragraph_index=0,
        sentence_index=0,
        global_sentence_index=0,
        text="Noether's theorem discovery.",
        char_count=27,
    )
    mention = MentionModel(
        id=mention_id,
        document_id=doc_id,
        sentence_id=sent_id,
        page_number=1,
        paragraph_index=0,
        sentence_index=0,
        mention_type="CONCEPT",
        raw_text="Noether's theorem",
        normalized_text="noether's theorem",
        start_char=0,
        end_char=17,
        extraction_method="spacy_noun_chunks",
        model_version="1.0.0",
    )
    db_session.add_all([doc, page, para, sent, mention])
    await db_session.commit()

    # 1. Trigger Omission Analysis API
    res1 = await async_client.post(f"/api/v1/documents/{doc_id}/analyze-omissions")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["document_id"] == str(doc_id)
    assert len(data1["candidates"]) >= 1

    cand_id = data1["candidates"][0]["id"]

    # 2. Retrieve Omission Summary API
    res2 = await async_client.get(f"/api/v1/documents/{doc_id}/omissions")
    assert res2.status_code == 200
    assert res2.json()["id"] == data1["id"]

    # 3. Retrieve Candidate Details API
    res3 = await async_client.get(f"/api/v1/documents/{doc_id}/omissions/candidates/{cand_id}")
    assert res3.status_code == 200
    assert res3.json()["id"] == cand_id
    assert "score_breakdown" in res3.json()
