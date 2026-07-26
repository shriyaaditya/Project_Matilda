import pytest
from httpx import AsyncClient

from app.services.concept_extractor import ConceptExtractor
from app.services.person_extractor import PersonExtractor
from tests.fixtures.pdf_fixtures import create_blank_pdf, create_sample_text_pdf


def test_person_extractor_rules() -> None:
    extractor = PersonExtractor()
    text = "Dr. Rosalind Franklin used X-ray crystallography to study DNA."

    mentions = extractor.extract_person_mentions(text)
    assert len(mentions) == 1

    raw_text, norm_text, start_c, end_c, conf = mentions[0]
    assert raw_text == "Rosalind Franklin"
    assert norm_text == "rosalind franklin"
    assert start_c == 4
    assert end_c == 21
    # Rule 1 verification: confidence MUST be None (NULL)
    assert conf is None


def test_person_extraction_surnames_and_initials() -> None:
    extractor = PersonExtractor()

    # Rule 3 verification: surface variants preserved distinct
    t1 = "Professor Franklin was a pioneering chemist."
    m1 = extractor.extract_person_mentions(t1)
    assert len(m1) == 1
    assert m1[0][0] == "Franklin"

    t2 = "Dr. R. Franklin published her analysis."
    m2 = extractor.extract_person_mentions(t2)
    assert len(m2) == 1
    assert m2[0][0] == "R. Franklin"


def test_multiple_people_in_sentence() -> None:
    extractor = PersonExtractor()
    text = "James Watson, Francis Crick, and Dr. Rosalind Franklin worked on molecular structure."
    mentions = extractor.extract_person_mentions(text)
    raw_names = [m[0] for m in mentions]

    assert "Rosalind Franklin" in raw_names
    assert len(mentions) >= 2


def test_concept_extractor_dynamic_phrases() -> None:
    extractor = ConceptExtractor()
    text = "X-ray crystallography was used to analyze molecular structure."

    concepts = extractor.extract_concept_mentions(text)
    raw_concepts = [c[0] for c in concepts]

    assert any("crystallography" in c.lower() or "structure" in c.lower() for c in raw_concepts)
    # Check offsets preserved without mutating raw text
    for raw, _norm, s_char, e_char, conf in concepts:
        assert conf is None
        assert text[s_char:e_char] == raw


def test_false_positive_concept_filtering() -> None:
    extractor = ConceptExtractor()
    # Sentence with noise terms: 'the chapter', 'figure 3', 'the method'
    text = "The chapter presents the method in figure 3 for analyzing nuclear fission."

    concepts = extractor.extract_concept_mentions(text)
    raw_concepts = [c[0].lower() for c in concepts]

    # Verify noise terms are filtered out
    assert "chapter" not in raw_concepts
    assert "method" not in raw_concepts
    assert "figure 3" not in raw_concepts
    # Verify valid domain concept remains
    assert any("fission" in c for c in raw_concepts)


def test_person_concept_overlap_prevention() -> None:
    person_extractor = PersonExtractor()
    concept_extractor = ConceptExtractor()

    text = "Dr. Rosalind Franklin studied X-ray crystallography."
    person_mentions = person_extractor.extract_person_mentions(text)
    person_spans = [(m[2], m[3]) for m in person_mentions]

    concept_mentions = concept_extractor.extract_concept_mentions(text, person_spans=person_spans)
    concept_raws = [c[0] for c in concept_mentions]

    # Rule 5 verification: PERSON name "Rosalind Franklin" MUST NOT appear as a CONCEPT
    assert "Rosalind Franklin" not in concept_raws
    assert "Rosalind" not in concept_raws
    assert "Franklin" not in concept_raws
    assert any("crystallography" in c for c in concept_raws)


@pytest.mark.asyncio
async def test_extraction_api_flow(async_client: AsyncClient) -> None:
    # 1. Upload sample text PDF
    pdf_bytes = create_sample_text_pdf()
    files = {"file": ("ch1.pdf", pdf_bytes, "application/pdf")}

    upload_res = await async_client.post("/api/v1/documents/upload", files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 2. Extract mentions
    extract_res = await async_client.post(f"/api/v1/documents/{doc_id}/extract")
    assert extract_res.status_code == 200
    summary = extract_res.json()

    assert summary["document_id"] == doc_id
    assert summary["is_already_extracted"] is False
    assert summary["person_mentions_count"] >= 1

    # 3. Test Idempotency: Second call without force_reextract returns is_already_extracted = True
    extract_res2 = await async_client.post(f"/api/v1/documents/{doc_id}/extract")
    assert extract_res2.status_code == 200
    assert extract_res2.json()["is_already_extracted"] is True

    # 4. Fetch extracted mentions with type filter
    mentions_res = await async_client.get(f"/api/v1/documents/{doc_id}/mentions?type=PERSON")
    assert mentions_res.status_code == 200
    persons = mentions_res.json()
    assert len(persons) >= 1
    assert persons[0]["mention_type"] == "PERSON"
    assert persons[0]["confidence"] is None  # Rule 1 verification
    assert "page_number" in persons[0]
    assert "paragraph_index" in persons[0]
    assert "sentence_index" in persons[0]


@pytest.mark.asyncio
async def test_extraction_blank_pdf(async_client: AsyncClient) -> None:
    pdf_bytes = create_blank_pdf()
    files = {"file": ("blank.pdf", pdf_bytes, "application/pdf")}

    upload_res = await async_client.post("/api/v1/documents/upload", files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    extract_res = await async_client.post(f"/api/v1/documents/{doc_id}/extract")
    assert extract_res.status_code == 200
    summary = extract_res.json()
    assert summary["person_mentions_count"] == 0
    assert summary["concept_mentions_count"] == 0
