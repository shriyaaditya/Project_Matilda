import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domain.graph import (
    GraphD3Export,
    GraphMetrics,
    GraphNode,
    GraphStats,
)
from app.services.graph_service import GraphService

router = APIRouter()


@router.get(
    "/stats",
    response_model=GraphStats,
    summary="Get Knowledge Graph Statistics",
    description="Returns total node and edge counts grouped by node and edge types, along with graph density.",
)
async def get_graph_stats(db: AsyncSession = Depends(get_db)) -> GraphStats:
    service = GraphService(db)
    return await service.get_stats()


@router.get(
    "/people/{id_or_qid}",
    summary="Get Person Node & Historical Annotations",
    description="Returns graph node and curated historical annotations for a person by UUID or Wikidata QID.",
)
async def get_person_node(
    id_or_qid: str, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    service = GraphService(db)
    result = await service.get_person(id_or_qid)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person node '{id_or_qid}' not found in knowledge graph.",
        )
    node, annotation = result
    return {
        "person": node,
        "annotation": annotation,
    }


@router.get(
    "/concepts/{id_or_label}",
    summary="Get Concept Node & Contributor Scientists",
    description="Returns concept node and list of scientists who CONTRIBUTED_TO it.",
)
async def get_concept_node(
    id_or_label: str, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    service = GraphService(db)
    result = await service.get_concept(id_or_label)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept node '{id_or_label}' not found in knowledge graph.",
        )
    concept_node, contributors = result
    return {
        "concept": concept_node,
        "contributors": contributors,
    }


@router.get(
    "/neighbors/{node_id}",
    summary="Get Connected Neighbor Nodes",
    description="Returns adjacent graph nodes with edge type and provenance metadata.",
)
async def get_node_neighbors(
    node_id: uuid.UUID,
    edge_type: str | None = Query(None, description="Optional edge type filter"),
    direction: str = Query("both", description="Edge direction: in, out, or both"),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    service = GraphService(db)
    raw_neighbors = await service.get_neighbors(
        node_id=node_id, edge_type=edge_type, direction=direction
    )
    return [
        {
            "node": n,
            "edge_type": etype,
            "provenance": prov,
        }
        for n, etype, prov in raw_neighbors
    ]


@router.get(
    "/paths/shortest",
    response_model=list[GraphNode],
    summary="Get Shortest Graph Path",
    description="Returns the shortest node path sequence connecting source and target nodes using NetworkX.",
)
async def get_shortest_path(
    source_node_id: uuid.UUID,
    target_node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[GraphNode]:
    service = GraphService(db)
    path = await service.get_shortest_path(source_id=source_node_id, target_id=target_node_id)
    if not path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No graph path exists between node {source_node_id} and {target_node_id}.",
        )
    return path


@router.get(
    "/metrics/{node_id}",
    response_model=GraphMetrics,
    summary="Get Structural Graph Centrality Metrics",
    description="Returns NetworkX structural centrality metrics (degree, PageRank, betweenness). NOT Matilda's final omission score.",
)
async def get_node_metrics(
    node_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> GraphMetrics:
    service = GraphService(db)
    metrics = await service.get_metrics(node_id)
    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found for metrics calculation.",
        )
    return metrics


@router.get(
    "/export/d3",
    response_model=GraphD3Export,
    summary="Export D3 Force-Directed Schema",
    description="Returns full graph JSON in D3 force-directed nodes[] and edges[] format.",
)
async def export_d3_graph(db: AsyncSession = Depends(get_db)) -> GraphD3Export:
    service = GraphService(db)
    return await service.export_d3()


@router.get(
    "/nodes",
    summary="List Knowledge Graph Nodes",
    description="Returns list of graph nodes from Supabase PostgreSQL.",
)
async def get_graph_nodes(
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    service = GraphService(db)
    d3 = await service.export_d3()
    return d3.nodes[:limit]


@router.get(
    "/edges",
    summary="List Knowledge Graph Edges",
    description="Returns list of graph edges from Supabase PostgreSQL.",
)
async def get_graph_edges(
    limit: int = Query(300, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    service = GraphService(db)
    d3 = await service.export_d3()
    return d3.edges[:limit]
