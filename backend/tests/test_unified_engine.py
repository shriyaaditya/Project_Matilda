import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import DocumentModel, PageModel, ParagraphModel, SentenceModel
from app.db.models.mention import MentionModel
from app.db.models.person import CanonicalPersonModel
from app.db.models.resolution import EntityResolutionModel
from app.services.evidence_fuser import EvidenceFuser
from app.services.evidence_normalizer import EvidenceNormalizer
from app.services.explanation_generator import ExplanationGenerator
from app.services.source_deduplicator import SourceDeduplicator
from app.services.unified_engine import UnifiedEngine
from app.services.unified_eval_hook import UnifiedEvaluationHook


def test_claim_aware_evidence_quality() -> None:
    normalizer = EvidenceNormalizer()

    # Direct P800 notable work claim -> 0.90 direct
    score_p800, direct_p800 = normalizer.evaluate_claim_aware_quality({"source_uri": "wikidata:Q7065#P800"})
    assert score_p800 == 0.90
    assert direct_p800 is True

    # P101 field claim -> 0.30 context only
    score_p101, direct_p101 = normalizer.evaluate_claim_aware_quality({"source_uri": "wikidata:Q7065#P101"})
    assert score_p101 == 0.30
    assert direct_p101 is False

    # P108 employer claim -> 0.20 context only
    score_p108, direct_p108 = normalizer.evaluate_claim_aware_quality({"source_uri": "wikidata:Q7065#P108"})
    assert score_p108 == 0.20
    assert direct_p108 is False


def test_normalized_source_deduplication() -> None:
    dedup = SourceDeduplicator()

    raw_sources = [
        {"source_uri": "https://doi.org/10.1038/nature01234"},
        {"source_uri": "doi:10.1038/nature01234"},
        {"source_uri": "10.1038/nature01234"},
        {"source_uri": "wikidata:Q7065#P800"},
    ]

    unique, log = dedup.deduplicate_evidence_sources(raw_sources)
    assert len(unique) == 2  # The 3 DOIs reduce to 1, plus P800
    assert len(log) == 2


def test_bounded_fusion_cap_without_direct_concept_evidence() -> None:
    fuser = EvidenceFuser()

    # 3 context-only sources (P101, P108, openalex topic)
    sources = [
        {"source_uri": "wikidata:Q7065#P101"},
        {"source_uri": "wikidata:Q7065#P108"},
        {"source_uri": "openalex:W12345"},
    ]

    fused_score, strength, breakdown = fuser.fuse_evidence(sources, base_phase_score=0.40)
    # Fused score must be capped at 0.50 (WEAK) because no direct concept evidence exists
    assert fused_score <= 0.50
    assert strength == "WEAK"
    assert breakdown.has_direct_concept_evidence is False


def test_template_explanation_generation() -> None:
    expl = ExplanationGenerator.generate_explanation(
        finding_type="POTENTIAL_OMISSION",
        person_label="Emmy Noether",
        concept_label="Noether's theorem",
        evidence_strength="STRONG",
    )
    assert "Emmy Noether was not identified" in expl
    assert "strong" in expl.lower()


def test_unified_eval_hook_metrics() -> None:
    metrics = UnifiedEvaluationHook.evaluate_unified_findings(
        pred_omissions=["Q7065"],
        gt_omissions=["Q7065"],
        pred_credits=["Q7065"],
        gt_credits=["Q7065"],
    )
    assert metrics.omission_f1 == 1.0
    assert metrics.credit_f1 == 1.0
    assert metrics.overall_evidence_coverage == 1.0


@pytest.mark.asyncio
async def test_unified_engine_end_to_end(db_session: AsyncSession) -> None:
    doc_id = uuid.uuid4()
    page_id = uuid.uuid4()
    para_id = uuid.uuid4()
    sent_id = uuid.uuid4()
    m1_id = uuid.uuid4()
    m2_id = uuid.uuid4()
    person_id = uuid.uuid4()

    doc = DocumentModel(
        id=doc_id,
        filename="unified_paper.pdf",
        file_size_bytes=3072,
        sha256_hash=f"hash_{doc_id.hex}",
        file_path="/tmp/unified.pdf",
        page_count=1,
        status="PARSED",
        created_at=datetime.now(UTC),
    )
    page = PageModel(id=page_id, document_id=doc_id, page_number=1, has_extractable_text=True, raw_text="Emmy Noether developed Noether's theorem.")
    para = ParagraphModel(id=para_id, page_id=page_id, document_id=doc_id, paragraph_index=0, text="Emmy Noether developed Noether's theorem.")
    sent = SentenceModel(
        id=sent_id,
        paragraph_id=para_id,
        document_id=doc_id,
        page_number=1,
        paragraph_index=0,
        sentence_index=0,
        global_sentence_index=0,
        text="Emmy Noether developed Noether's theorem.",
        char_count=41,
    )
    m_person = MentionModel(
        id=m1_id,
        document_id=doc_id,
        sentence_id=sent_id,
        page_number=1,
        paragraph_index=0,
        sentence_index=0,
        mention_type="PERSON",
        raw_text="Emmy Noether",
        normalized_text="emmy noether",
        start_char=0,
        end_char=12,
        extraction_method="spacy_ner",
        model_version="1.0.0",
    )
    m_concept = MentionModel(
        id=m2_id,
        document_id=doc_id,
        sentence_id=sent_id,
        page_number=1,
        paragraph_index=0,
        sentence_index=0,
        mention_type="CONCEPT",
        raw_text="Noether's theorem",
        normalized_text="noether's theorem",
        start_char=23,
        end_char=40,
        extraction_method="spacy_noun_chunks",
        model_version="1.0.0",
    )
    person = CanonicalPersonModel(
        id=person_id,
        canonical_name="Emmy Noether",
        wikidata_qid="Q7099",
        created_at=datetime.now(UTC),
    )
    resolution = EntityResolutionModel(
        id=uuid.uuid4(),
        document_id=doc_id,
        mention_id=m1_id,
        person_id=person_id,
        status="RESOLVED",
        resolution_score=1.0,
        matched_qid="Q7099",
        evidence={"method": "exact_match"},
        created_at=datetime.now(UTC),
    )

    db_session.add_all([doc, page, para, sent, m_person, m_concept, person, resolution])
    await db_session.commit()

    engine = UnifiedEngine(db_session)
    summary = await engine.analyze_document_unified(doc_id, force_reanalyze=True)

    assert summary.document_id == doc_id
    assert summary.total_findings_count >= 1
    assert summary.evidence_attention_score >= 0.0
    assert len(summary.findings) >= 1

    f = summary.findings[0]
    assert f.person_label == "Emmy Noether"
    assert f.evidence_strength in ["STRONG", "MODERATE", "WEAK", "INSUFFICIENT"]


@pytest.mark.asyncio
async def test_unified_api_endpoints(async_client: AsyncClient, db_session: AsyncSession) -> None:
    doc_id = uuid.uuid4()
    page_id = uuid.uuid4()
    para_id = uuid.uuid4()
    sent_id = uuid.uuid4()
    m1_id = uuid.uuid4()
    m2_id = uuid.uuid4()

    doc = DocumentModel(
        id=doc_id,
        filename="api_unified_test.pdf",
        file_size_bytes=1000,
        sha256_hash=f"hash_{doc_id.hex}",
        file_path="/tmp/api_unified.pdf",
        page_count=1,
        status="PARSED",
        created_at=datetime.now(UTC),
    )
    page = PageModel(id=page_id, document_id=doc_id, page_number=1, has_extractable_text=True, raw_text="Chien-Shiung Wu demonstrated parity violation.")
    para = ParagraphModel(id=para_id, page_id=page_id, document_id=doc_id, paragraph_index=0, text="Chien-Shiung Wu demonstrated parity violation.")
    sent = SentenceModel(
        id=sent_id,
        paragraph_id=para_id,
        document_id=doc_id,
        page_number=1,
        paragraph_index=0,
        sentence_index=0,
        global_sentence_index=0,
        text="Chien-Shiung Wu demonstrated parity violation.",
        char_count=45,
    )
    m_person = MentionModel(
        id=m1_id,
        document_id=doc_id,
        sentence_id=sent_id,
        page_number=1,
        paragraph_index=0,
        sentence_index=0,
        mention_type="PERSON",
        raw_text="Chien-Shiung Wu",
        normalized_text="chien-shiung wu",
        start_char=0,
        end_char=15,
        extraction_method="spacy_ner",
        model_version="1.0.0",
    )
    m_concept = MentionModel(
        id=m2_id,
        document_id=doc_id,
        sentence_id=sent_id,
        page_number=1,
        paragraph_index=0,
        sentence_index=0,
        mention_type="CONCEPT",
        raw_text="parity violation",
        normalized_text="parity violation",
        start_char=29,
        end_char=45,
        extraction_method="spacy_noun_chunks",
        model_version="1.0.0",
    )
    db_session.add_all([doc, page, para, sent, m_person, m_concept])
    await db_session.commit()

    # 1. Trigger Unified Analysis API
    res1 = await async_client.post(f"/api/v1/documents/{doc_id}/analyze-unified")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["document_id"] == str(doc_id)
    assert len(data1["findings"]) >= 1

    finding_id = data1["findings"][0]["id"]

    # 2. Retrieve Unified Summary API
    res2 = await async_client.get(f"/api/v1/documents/{doc_id}/unified")
    assert res2.status_code == 200
    assert res2.json()["id"] == data1["id"]

    # 3. Retrieve Finding Details API
    res3 = await async_client.get(f"/api/v1/documents/{doc_id}/unified/findings/{finding_id}")
    assert res3.status_code == 200
    assert res3.json()["id"] == finding_id
    assert "score_breakdown" in res3.json()
