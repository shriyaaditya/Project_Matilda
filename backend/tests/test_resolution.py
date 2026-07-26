from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.resolution_matcher import ResolutionMatcher
from app.services.wikidata_service import WikidataService
from tests.fixtures.pdf_fixtures import create_sample_text_pdf


def test_matcher_full_name_strong_context_resolution() -> None:
    matcher = ResolutionMatcher()
    candidates = [
        {
            "qid": "Q7474",
            "canonical_name": "Rosalind Franklin",
            "description": "English chemist and X-ray crystallographer",
            "aliases": ["Rosalind Elsie Franklin"],
            "occupations": ["chemist", "biophysicist", "crystallographer"],
            "birth_year": 1920,
            "death_year": 1958,
        }
    ]

    status, score, matched, evidence = matcher.evaluate_candidates(
        mention_raw="Rosalind Franklin",
        nearby_concepts=["X-ray crystallography", "biophysics"],
        nearby_text="In 1952, Rosalind Franklin discovered the B-form structure of DNA.",
        candidates=candidates,
    )

    assert status == "RESOLVED"
    assert matched["qid"] == "Q7474"
    assert score >= 0.65
    assert evidence.name_score == 0.45
    assert len(evidence.matched_concepts) >= 2


def test_matcher_full_name_weak_context_ambiguous() -> None:
    matcher = ResolutionMatcher()
    candidates = [
        {
            "qid": "Q7474",
            "canonical_name": "Rosalind Franklin",
            "description": "English chemist and X-ray crystallographer",
            "aliases": [],
            "occupations": ["crystallographer"],
        }
    ]

    status, score, matched, evidence = matcher.evaluate_candidates(
        mention_raw="Rosalind Franklin",
        nearby_concepts=[],
        nearby_text="Rosalind Franklin attended school in London.",
        candidates=candidates,
    )

    assert status == "AMBIGUOUS"
    assert matched is None


def test_matcher_surname_with_2_concepts_resolution() -> None:
    matcher = ResolutionMatcher()
    candidates = [
        {
            "qid": "Q7474",
            "canonical_name": "Rosalind Franklin",
            "description": "English chemist and X-ray crystallographer",
            "aliases": [],
            "occupations": ["crystallographer", "chemist"],
            "birth_year": 1920,
            "death_year": 1958,
        },
        {
            "qid": "Q34969",
            "canonical_name": "Benjamin Franklin",
            "description": "American polymath, statesman, and scientist",
            "aliases": [],
            "occupations": ["statesman", "inventor"],
            "birth_year": 1706,
            "death_year": 1790,
        },
    ]

    status, score, matched, evidence = matcher.evaluate_candidates(
        mention_raw="Franklin",
        nearby_concepts=["X-ray crystallography", "chemist"],
        nearby_text="Franklin conducted experiments in c. 1952.",
        candidates=candidates,
    )

    assert status == "RESOLVED"
    assert matched["qid"] == "Q7474"
    assert score >= 0.55
    assert len(evidence.matched_concepts) >= 2


def test_adversarial_surname_single_concept_weak_similarity_ambiguous() -> None:
    matcher = ResolutionMatcher()
    candidates = [
        {
            "qid": "Q7474",
            "canonical_name": "Rosalind Franklin",
            "description": "English chemist and X-ray crystallographer",
            "aliases": [],
            "occupations": ["crystallographer"],
        },
        {
            "qid": "Q34969",
            "canonical_name": "Benjamin Franklin",
            "description": "American polymath",
            "aliases": [],
            "occupations": [],
        },
    ]

    status, score, matched, evidence = matcher.evaluate_candidates(
        mention_raw="Franklin",
        nearby_concepts=["crystallographer"],
        nearby_text="Franklin wrote a paper.",
        candidates=candidates,
    )

    assert status == "AMBIGUOUS"
    assert matched is None


def test_adversarial_initials_single_concept_ambiguous() -> None:
    matcher = ResolutionMatcher()
    candidates = [
        {
            "qid": "Q7474",
            "canonical_name": "Rosalind Franklin",
            "description": "English chemist",
            "aliases": [],
            "occupations": [],
        }
    ]

    status, score, matched, evidence = matcher.evaluate_candidates(
        mention_raw="R. Franklin",
        nearby_concepts=["chemist"],
        nearby_text="R. Franklin was mentioned.",
        candidates=candidates,
    )

    assert status == "AMBIGUOUS"
    assert matched is None


def test_adversarial_surname_zero_concepts_unresolved_or_ambiguous() -> None:
    matcher = ResolutionMatcher()
    candidates = [
        {
            "qid": "Q7474",
            "canonical_name": "Rosalind Franklin",
            "description": "English chemist",
            "aliases": [],
            "occupations": [],
        },
        {
            "qid": "Q34969",
            "canonical_name": "Benjamin Franklin",
            "description": "American polymath",
            "aliases": [],
            "occupations": [],
        },
    ]

    status, score, matched, evidence = matcher.evaluate_candidates(
        mention_raw="Franklin",
        nearby_concepts=[],
        nearby_text="Franklin published the paper.",
        candidates=candidates,
    )

    assert status in ["AMBIGUOUS", "UNRESOLVED"]
    assert matched is None


def test_matcher_unknown_person_unresolved() -> None:
    matcher = ResolutionMatcher()
    status, score, matched, evidence = matcher.evaluate_candidates(
        mention_raw="Fictional Person Name X",
        nearby_concepts=[],
        nearby_text="Some text",
        candidates=[],
    )

    assert status == "UNRESOLVED"
    assert score == 0.0
    assert matched is None


@pytest.mark.asyncio
async def test_resolution_api_flow(async_client: AsyncClient) -> None:
    pdf_bytes = create_sample_text_pdf()
    files = {"file": ("ch1.pdf", pdf_bytes, "application/pdf")}

    upload_res = await async_client.post("/api/v1/documents/upload", files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    extract_res = await async_client.post(f"/api/v1/documents/{doc_id}/extract")
    assert extract_res.status_code == 200

    mock_candidates = [
        {
            "qid": "Q9333",
            "canonical_name": "Chien-Shiung Wu",
            "description": "Chinese-American experimental physicist who disproved law of conservation of parity in weak nuclear interactions",
            "aliases": ["C. S. Wu"],
            "birth_year": 1912,
            "death_year": 1997,
            "occupations": ["landmark parity experiment", "weak nuclear interactions"],
        }
    ]

    with patch.object(WikidataService, "search_entities", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_candidates

        resolve_res = await async_client.post(f"/api/v1/documents/{doc_id}/resolve")
        assert resolve_res.status_code == 200
        summary = resolve_res.json()

        assert summary["document_id"] == doc_id
        assert summary["total_person_mentions"] >= 1
        assert summary["is_already_resolved"] is False

        # Print debug resolutions
        debug_res = await async_client.get(f"/api/v1/documents/{doc_id}/resolutions")
        print("DEBUG RESOLUTIONS:", debug_res.json())

        resolve_res2 = await async_client.post(f"/api/v1/documents/{doc_id}/resolve")
        assert resolve_res2.status_code == 200
        assert resolve_res2.json()["is_already_resolved"] is True

        people_res = await async_client.get(f"/api/v1/documents/{doc_id}/people")
        assert people_res.status_code == 200
        people = people_res.json()
        assert len(people) >= 1
        assert any("Chien-Shiung Wu" in p["canonical_name"] for p in people)

        resolutions_res = await async_client.get(f"/api/v1/documents/{doc_id}/resolutions")
        assert resolutions_res.status_code == 200
        resolutions = resolutions_res.json()
        assert len(resolutions) >= 1
        res_id = resolutions[0]["id"]
        assert "evidence" in resolutions[0]

        exp_res = await async_client.get(f"/api/v1/resolutions/{res_id}/explanation")
        assert exp_res.status_code == 200
        explanation = exp_res.json()
        assert explanation["id"] == res_id
        assert "evidence_summary" in explanation["evidence"]
