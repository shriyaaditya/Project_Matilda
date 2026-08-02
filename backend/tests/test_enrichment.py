import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.enrich_dataset import run_enrichment
from app.services.graph_enricher import GraphEnricher
from app.services.openalex_service import OpenAlexService
from app.services.qid_resolver import QIDResolver
from app.services.wikidata_service import WikidataService


@pytest.mark.asyncio
async def test_qid_resolution_success(db_session: AsyncSession) -> None:
    resolver = QIDResolver(db_session)
    mock_candidates = [
        {
            "qid": "Q9333",
            "canonical_name": "Chien-Shiung Wu",
            "description": "Chinese-American experimental physicist",
            "occupations": ["experimental physicist", "nuclear physicist"],
        }
    ]
    with patch.object(WikidataService, "search_entities", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_candidates
        qid, status, score, cands = await resolver.resolve_person_qid(
            "Chien-Shiung Wu", {"primary_field": "Physics", "country": "China / United States"}
        )
        assert qid == "Q9333"
        assert status == "QID_VERIFIED"
        assert score >= 0.75


@pytest.mark.asyncio
async def test_qid_resolution_ambiguous_rejection(db_session: AsyncSession) -> None:
    resolver = QIDResolver(db_session)
    # Low confidence candidate (name doesn't match primary field/country)
    mock_candidates = [
        {
            "qid": "Q9999",
            "canonical_name": "Unrelated Name Match",
            "description": "Botanist from Germany",
            "occupations": ["botanist"],
        }
    ]
    with patch.object(WikidataService, "search_entities", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_candidates
        qid, status, score, cands = await resolver.resolve_person_qid(
            "Chien-Shiung Wu", {"primary_field": "Physics", "country": "China / United States"}
        )
        assert qid is None
        assert status == "PENDING_WIKIDATA_VERIFICATION"
        assert score < 0.75


@pytest.mark.asyncio
async def test_contributed_to_strictness_and_provenance(db_session: AsyncSession) -> None:
    enricher = GraphEnricher(db_session)
    seed_data = {
        "version": "1.0.0",
        "nodes": [
            {
                "node_type": "PERSON",
                "label": "Rosalind Franklin",
                "wikidata_qid": "Q7474",
                "properties": {"primary_field": "Molecular Biology", "country": "United Kingdom"},
            }
        ],
    }

    mock_details = {
        "birth_year": 1920,
        "death_year": 1958,
        "aliases": ["Rosalind Elsie Franklin"],
        "occupations": ["chemist", "biophysicist"],
        "employers": ["King's College London"],
        "notable_works": ["DNA B-form Structure"],
        "description": "British chemist",
    }
    mock_openalex_works = {
        "results": [
            {
                "id": "https://openalex.org/W12345",
                "title": "Molecular Configuration in Sodium Thymonucleate",
                "cited_by_count": 500,
                "publication_year": 1953,
            }
        ]
    }

    with patch.object(WikidataService, "get_entity_details", new_callable=AsyncMock) as mock_wiki, \
         patch.object(OpenAlexService, "search_author_by_identifier", new_callable=AsyncMock) as mock_oa_author, \
         patch.object(OpenAlexService, "get_author_concepts_and_works", new_callable=AsyncMock) as mock_oa_works:

        mock_wiki.return_value = mock_details
        mock_oa_author.return_value = [{"id": "https://openalex.org/A500"}]
        mock_oa_works.return_value = mock_openalex_works

        enriched = await enricher.enrich_dataset(seed_data)

        # 1. P101 / primary_field creates ASSOCIATED_WITH, never CONTRIBUTED_TO
        assoc_edges = [e for e in enriched["edges"] if e["edge_type"] == "ASSOCIATED_WITH"]
        assert len(assoc_edges) >= 1
        assert assoc_edges[0]["target_label"] == "Molecular Biology"

        # 2. P108 employer creates WORKED_AT
        worked_edges = [e for e in enriched["edges"] if e["edge_type"] == "WORKED_AT"]
        assert len(worked_edges) >= 1
        assert worked_edges[0]["target_label"] == "King's College London"

        # 3. P800 notable work and OpenAlex publications create CONTRIBUTED_TO edges
        contrib_edges = [e for e in enriched["edges"] if e["edge_type"] == "CONTRIBUTED_TO"]
        assert len(contrib_edges) == 2
        contrib_targets = {e["target_label"] for e in contrib_edges}
        assert "DNA B-form Structure" in contrib_targets
        assert "Molecular Configuration in Sodium Thymonucleate" in contrib_targets
        assert all("source_uri" in e["provenance"] for e in contrib_edges)

        # 4. OpenAlex works are also stored in contribution_candidates
        candidates = enriched["contribution_candidates"]
        assert len(candidates) >= 1
        assert candidates[0]["candidate_concept_title"] == "Molecular Configuration in Sodium Thymonucleate"


@pytest.mark.asyncio
async def test_openalex_authorship_and_collaboration_edges(db_session: AsyncSession) -> None:
    enricher = GraphEnricher(db_session)
    seed_data = {
        "version": "1.0.0",
        "nodes": [
            {
                "node_type": "PERSON",
                "label": "Rosalind Franklin",
                "wikidata_qid": "Q7474",
                "properties": {"primary_field": "Molecular Biology"},
            }
        ],
    }

    mock_openalex_works = {
        "results": [
            {
                "id": "https://openalex.org/W1001",
                "title": "Structure of Sodium Thymonucleate",
                "cited_by_count": 300,
                "publication_year": 1953,
                "authorships": [
                    {
                        "author": {
                            "id": "https://openalex.org/A500",
                            "display_name": "Rosalind Franklin",
                            "orcid": "https://orcid.org/0000-0000-0000-0000",
                        }
                    },
                    {
                        "author": {
                            "id": "https://openalex.org/A501",
                            "display_name": "Raymond Gosling",
                            "orcid": None,
                        }
                    },
                    {
                        "author": {
                            "id": None,
                            "display_name": "Raymond Gosling",  # Duplicate co-author without ID
                        }
                    },
                ],
            }
        ]
    }

    with patch.object(WikidataService, "get_entity_details", new_callable=AsyncMock) as mock_wiki, \
         patch.object(OpenAlexService, "search_author_by_identifier", new_callable=AsyncMock) as mock_oa_author, \
         patch.object(OpenAlexService, "get_author_concepts_and_works", new_callable=AsyncMock) as mock_oa_works:

        mock_wiki.return_value = None
        mock_oa_author.return_value = [{"id": "https://openalex.org/A500"}]
        mock_oa_works.return_value = mock_openalex_works

        enriched = await enricher.enrich_dataset(seed_data)

        # 1. AUTHORED edge verification
        authored_edges = [e for e in enriched["edges"] if e["edge_type"] == "AUTHORED"]
        assert len(authored_edges) == 1
        assert authored_edges[0]["source_label"] == "Rosalind Franklin"
        assert authored_edges[0]["target_label"] == "Structure of Sodium Thymonucleate"
        assert authored_edges[0]["provenance"]["source_uri"] == "https://openalex.org/W1001"

        # 2. COLLABORATED_WITH edge verification
        collab_edges = [e for e in enriched["edges"] if e["edge_type"] == "COLLABORATED_WITH"]
        assert len(collab_edges) == 2  # generated per authorship entry matching co-author
        assert collab_edges[0]["source_label"] == "Rosalind Franklin"
        assert collab_edges[0]["target_label"] == "Raymond Gosling"

        # 3. Person node deduplication verification (Raymond Gosling should exist as 1 unique PERSON node)
        person_nodes = [n for n in enriched["nodes"] if n["node_type"] == "PERSON"]
        labels = [n["label"] for n in person_nodes]
        assert labels.count("Raymond Gosling") == 1
        assert labels.count("Rosalind Franklin") == 1

        # 4. NetworkX Traversal Verification
        import networkx as nx
        G = nx.DiGraph()
        for node in enriched["nodes"]:
            G.add_node(node["label"], node_type=node["node_type"])
        for edge in enriched["edges"]:
            G.add_edge(edge["source_label"], edge["target_label"], edge_type=edge["edge_type"])

        # Check path from Rosalind Franklin -> Raymond Gosling
        assert G.has_edge("Rosalind Franklin", "Raymond Gosling")
        assert G.get_edge_data("Rosalind Franklin", "Raymond Gosling")["edge_type"] == "COLLABORATED_WITH"
        # Check path from Rosalind Franklin -> Structure of Sodium Thymonucleate
        assert G.has_edge("Rosalind Franklin", "Structure of Sodium Thymonucleate")
        assert G.get_edge_data("Rosalind Franklin", "Structure of Sodium Thymonucleate")["edge_type"] in ("CONTRIBUTED_TO", "AUTHORED")


@pytest.mark.asyncio
async def test_seed_file_remains_unmodified(tmp_path: Path) -> None:
    seed_file = Path("app/data/seed_women_stem.json")
    assert seed_file.is_file()

    with open(seed_file, "rb") as f:
        hash_before = hashlib.sha256(f.read()).hexdigest()

    output_file = tmp_path / "generated_women_stem_graph.json"

    # Mock Wikidata search to avoid hitting live network in automated pytest
    mock_candidates = [
        {
            "qid": "Q7474",
            "canonical_name": "Rosalind Franklin",
            "description": "British chemist",
            "occupations": ["chemist"],
        }
    ]

    with patch.object(WikidataService, "search_entities", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_candidates
        await run_enrichment(str(seed_file), str(output_file))

    with open(seed_file, "rb") as f:
        hash_after = hashlib.sha256(f.read()).hexdigest()

    assert hash_before == hash_after, "Seed input file was modified during enrichment execution!"
    assert output_file.is_file(), "Output enriched artifact was not created."


@pytest.mark.asyncio
async def test_citation_and_alias_graph_relationships() -> None:
    enricher = GraphEnricher(db=None)

    seed_data = {
        "nodes": [
            {
                "node_type": "PERSON",
                "label": "Rosalind Franklin",
                "properties": {
                    "primary_field": "Biophysics",
                    "country": "United Kingdom",
                    "aliases": ["R. E. Franklin", "H. E. Franklin"],
                },
            }
        ]
    }

    mock_openalex_works = {
        "results": [
            {
                "id": "https://openalex.org/W1001",
                "title": "Molecular Configuration in Sodium Thymonucleate",
                "doi": "https://doi.org/10.1038/171740a0",
                "publication_year": 1953,
                "cited_by_count": 1200,
                "authorships": [],
            }
        ]
    }

    mock_citing_works = {
        "results": [
            {
                "id": "https://openalex.org/W2002",
                "title": "Molecular Structure of Nucleic Acids",
                "doi": "https://doi.org/10.1038/171737a0",
                "publication_year": 1953,
                "cited_by_count": 5000,
            }
        ]
    }

    with patch.object(WikidataService, "get_entity_details", new_callable=AsyncMock) as mock_wiki, \
         patch.object(OpenAlexService, "search_author_by_identifier", new_callable=AsyncMock) as mock_oa_author, \
         patch.object(OpenAlexService, "get_author_concepts_and_works", new_callable=AsyncMock) as mock_oa_works, \
         patch.object(OpenAlexService, "get_related_or_citing_works", new_callable=AsyncMock) as mock_oa_citing:

        mock_wiki.return_value = {"aliases": ["R. E. Franklin"]}
        mock_oa_author.return_value = [{"id": "https://openalex.org/A500"}]
        mock_oa_works.return_value = mock_openalex_works
        mock_oa_citing.return_value = mock_citing_works

        enriched = await enricher.enrich_dataset(seed_data)

        # 1. ALIAS node & ALIAS_OF edge verification
        alias_nodes = [n for n in enriched["nodes"] if n["node_type"] == "ALIAS"]
        alias_labels = [n["label"] for n in alias_nodes]
        assert "R. E. Franklin" in alias_labels or "H. E. Franklin" in alias_labels

        alias_edges = [e for e in enriched["edges"] if e["edge_type"] == "ALIAS_OF"]
        assert len(alias_edges) >= 1
        assert alias_edges[0]["target_label"] == "Rosalind Franklin"

        # 2. PUBLICATION node & CITED_BY edge verification
        pub_nodes = [n for n in enriched["nodes"] if n["node_type"] == "PUBLICATION"]
        pub_titles = [n["label"] for n in pub_nodes]
        assert "Molecular Configuration in Sodium Thymonucleate" in pub_titles
        assert "Molecular Structure of Nucleic Acids" in pub_titles

        cited_edges = [e for e in enriched["edges"] if e["edge_type"] == "CITED_BY"]
        assert len(cited_edges) == 1
        assert cited_edges[0]["source_label"] == "Molecular Configuration in Sodium Thymonucleate"
        assert cited_edges[0]["target_label"] == "Molecular Structure of Nucleic Acids"
        assert cited_edges[0]["provenance"]["reference_text"] == "OpenAlex citation metadata"

