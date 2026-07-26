import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import DocumentModel, PageModel, ParagraphModel, SentenceModel
from app.db.models.mention import MentionModel
from app.db.models.person import CanonicalPersonModel
from app.db.models.resolution import EntityResolutionModel
from app.services.attribution_extractor import AttributionExtractor
from app.services.credit_engine import CreditEngine
from app.services.credit_eval_hook import CreditEvaluationHook
from app.services.evidence_comparator import EvidenceComparator


def test_attribution_extractor_verbs() -> None:
    extractor = AttributionExtractor()
    assert extractor.classify_verb_type("discover") == "DISCOVERY"
    assert extractor.classify_verb_type("develop") == "CONTRIBUTION"
    assert extractor.classify_verb_type("assist") == "SUPPORT"
    assert extractor.classify_verb_type("jointly") == "COLLABORATION"


def test_no_false_underattribution_when_evidence_aligns() -> None:
    comparator = EvidenceComparator()

    doc_claim = {
        "person_label": "Emmy Noether",
        "concept_label": "Noether's theorem",
        "attribution_type": "SUPPORTING_ROLE",
        "document_text": "Emmy Noether provided experimental evidence for Noether's theorem.",
    }
    evidence_records = [
        {
            "source_uri": "wikidata:Q7065#P800",
            "reference_text": "Emmy Noether produced experimental evidence supporting Noether's theorem.",
        }
    ]

    classification, summary, primary_evid, score = comparator.compare_attribution_against_evidence(
        doc_claim, evidence_records
    )
    # Supporting role verb matching evidence must NOT produce underattribution
    assert classification == "DOCUMENT_CREDIT_ALIGNS_WITH_EVIDENCE"


def test_semantic_role_mismatch_produces_underattribution() -> None:
    comparator = EvidenceComparator()

    doc_claim = {
        "person_label": "Emmy Noether",
        "concept_label": "Noether's theorem",
        "attribution_type": "SUPPORTING_ROLE",
        "document_text": "Emmy Noether assisted in discovering Noether's theorem.",
    }
    evidence_records = [
        {
            "source_uri": "wikidata:Q7065#P800",
            "reference_text": "Emmy Noether independently established Noether's theorem discovery.",
        }
    ]

    classification, summary, primary_evid, score = comparator.compare_attribution_against_evidence(
        doc_claim, evidence_records
    )
    assert classification == "POSSIBLE_UNDERATTRIBUTION"
    assert score >= 0.70


def test_weak_evidence_produces_insufficient_evidence_not_overattribution() -> None:
    comparator = EvidenceComparator()

    doc_claim = {
        "person_label": "Unverified Scientist",
        "concept_label": "Some Concept",
        "attribution_type": "DISCOVERY_CREDIT",
        "document_text": "Unverified Scientist discovered Some Concept.",
    }
    evidence_records = [
        {
            "source_uri": "seed_manifest:Unverified Scientist",
            "reference_text": "General field context for Unverified Scientist.",
        }
    ]

    classification, summary, primary_evid, score = comparator.compare_attribution_against_evidence(
        doc_claim, evidence_records
    )
    # Weak context evidence must produce INSUFFICIENT_EVIDENCE, never false overattribution
    assert classification == "INSUFFICIENT_EVIDENCE"


def test_credit_eval_hook_metrics() -> None:
    pred = ["Emmy Noether", "Chien-Shiung Wu"]
    gt = ["Emmy Noether", "Chien-Shiung Wu"]

    metrics = CreditEvaluationHook.evaluate_credit_discrepancies(pred, gt, total_negative_pool=50)
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1_score == 1.0


@pytest.mark.asyncio
async def test_credit_engine_end_to_end(db_session: AsyncSession) -> None:
    doc_id = uuid.uuid4()
    page_id = uuid.uuid4()
    para_id = uuid.uuid4()
    sent_id = uuid.uuid4()
    m1_id = uuid.uuid4()
    m2_id = uuid.uuid4()
    person_id = uuid.uuid4()

    doc = DocumentModel(
        id=doc_id,
        filename="credit_paper.pdf",
        file_size_bytes=2048,
        sha256_hash=f"hash_{doc_id.hex}",
        file_path="/tmp/credit.pdf",
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

    engine = CreditEngine(db_session)
    summary = await engine.analyze_document_credit(doc_id, force_reanalyze=True)

    assert summary.document_id == doc_id
    assert summary.total_attributions_extracted >= 1
    assert len(summary.attributions) >= 1

    attr = summary.attributions[0]
    assert attr.person_label == "Emmy Noether"
    assert attr.concept_label == "Noether's theorem"
    assert attr.discrepancy_classification in ["DOCUMENT_CREDIT_ALIGNS_WITH_EVIDENCE", "POSSIBLE_UNDERATTRIBUTION"]


@pytest.mark.asyncio
async def test_credit_api_endpoints(async_client: AsyncClient, db_session: AsyncSession) -> None:
    doc_id = uuid.uuid4()
    page_id = uuid.uuid4()
    para_id = uuid.uuid4()
    sent_id = uuid.uuid4()
    m1_id = uuid.uuid4()
    m2_id = uuid.uuid4()

    doc = DocumentModel(
        id=doc_id,
        filename="api_credit_test.pdf",
        file_size_bytes=1000,
        sha256_hash=f"hash_{doc_id.hex}",
        file_path="/tmp/api_credit.pdf",
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

    # 1. Trigger Credit Analysis API
    res1 = await async_client.post(f"/api/v1/documents/{doc_id}/analyze-credit")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["document_id"] == str(doc_id)
    assert len(data1["attributions"]) >= 1

    attr_id = data1["attributions"][0]["id"]

    # 2. Retrieve Credit Analysis Summary API
    res2 = await async_client.get(f"/api/v1/documents/{doc_id}/credit")
    assert res2.status_code == 200
    assert res2.json()["id"] == data1["id"]

    # 3. Retrieve Attribution Details API
    res3 = await async_client.get(f"/api/v1/documents/{doc_id}/credit/attributions/{attr_id}")
    assert res3.status_code == 200
    assert res3.json()["id"] == attr_id
    assert "score_breakdown" in res3.json()
