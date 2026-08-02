import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dataset_loader import DatasetLoader, DatasetValidationError
from app.services.graph_service import GraphService


def test_dataset_validator_invalid_duplicate_qid() -> None:
    loader = DatasetLoader(None)  # type: ignore[arg-type]
    bad_data = {
        "version": "1.0.0",
        "nodes": [
            {"node_type": "PERSON", "label": "Person A", "wikidata_qid": "Q100"},
            {"node_type": "PERSON", "label": "Person B", "wikidata_qid": "Q100"},
        ],
    }
    with pytest.raises(DatasetValidationError, match="Duplicate QID"):
        loader.validate_dataset_json(bad_data)


def test_dataset_validator_duplicate_person_label() -> None:
    loader = DatasetLoader(None)  # type: ignore[arg-type]
    bad_data = {
        "version": "1.0.0",
        "nodes": [
            {"node_type": "PERSON", "label": "Marie Curie", "wikidata_qid": "Q937"},
            {"node_type": "PERSON", "label": "Marie Curie", "wikidata_qid": "Q999"},
        ],
    }
    with pytest.raises(DatasetValidationError, match="Duplicate PERSON node label"):
        loader.validate_dataset_json(bad_data)


def test_dataset_validator_credit_context_missing_source() -> None:
    loader = DatasetLoader(None)  # type: ignore[arg-type]
    bad_data = {
        "version": "1.0.0",
        "nodes": [{"node_type": "PERSON", "label": "Person A", "wikidata_qid": "Q100"}],
        "annotations": [
            {
                "person_qid": "Q100",
                "contribution_summary": "Summary",
                "credit_context": "Uncredited work claim",
                "source_refs": [],  # Empty source refs -> INVALID
                "curation_status": "VERIFIED_HUMAN",
            }
        ],
    }
    with pytest.raises(DatasetValidationError, match="lacks mandatory authoritative source_refs"):
        loader.validate_dataset_json(bad_data)


@pytest.mark.asyncio
async def test_dataset_ingestion_flow(db_session: AsyncSession) -> None:
    loader = DatasetLoader(db_session)
    result = await loader.ingest_seed_dataset("app/data/generated_women_stem_graph.json")
    assert result["nodes_inserted"] >= 5
    assert result["edges_inserted"] >= 3

    # Test idempotency: re-running ingestion updates existing without duplicating
    result2 = await loader.ingest_seed_dataset("app/data/generated_women_stem_graph.json")
    assert result2["nodes_inserted"] == 0
    assert result2["edges_inserted"] == 0


@pytest.mark.asyncio
async def test_graph_service_traversal_and_metrics(db_session: AsyncSession) -> None:
    loader = DatasetLoader(db_session)
    await loader.ingest_seed_dataset("app/data/generated_women_stem_graph.json")

    service = GraphService(db_session)
    stats = await service.get_stats()
    assert stats.total_nodes >= 5
    assert stats.total_edges >= 3

    # Test person lookup by QID Q7474 (Rosalind Franklin)
    result = await service.get_person("Q7474")
    assert result is not None
    person_node, annotation = result
    assert person_node.label == "Rosalind Franklin"

    # Test metrics calculation
    metrics = await service.get_metrics(person_node.id)
    assert metrics is not None
    assert metrics.degree_centrality >= 0.0
    assert "NOT Matilda's final omission" in metrics.disclaimer


@pytest.mark.asyncio
async def test_graph_api_endpoints(async_client: AsyncClient, db_session: AsyncSession) -> None:
    loader = DatasetLoader(db_session)
    await loader.ingest_seed_dataset("app/data/generated_women_stem_graph.json")

    # 1. Stats endpoint
    stats_res = await async_client.get("/api/v1/graph/stats")
    assert stats_res.status_code == 200
    assert stats_res.json()["total_nodes"] >= 5

    # 2. Person endpoint
    person_res = await async_client.get("/api/v1/graph/people/Q7474")
    assert person_res.status_code == 200
    p_data = person_res.json()
    p_id = p_data["person"]["id"]
    assert p_data["person"]["label"] == "Rosalind Franklin"

    # 3. D3 export endpoint
    d3_res = await async_client.get("/api/v1/graph/export/d3")
    assert d3_res.status_code == 200
    d3_data = d3_res.json()
    assert "nodes" in d3_data
    assert "edges" in d3_data
    assert len(d3_data["nodes"]) >= 5

    # 4. Metrics endpoint
    metrics_res = await async_client.get(f"/api/v1/graph/metrics/{p_id}")
    assert metrics_res.status_code == 200
    assert "pagerank" in metrics_res.json()
