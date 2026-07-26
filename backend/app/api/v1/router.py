from fastapi import APIRouter

from app.api.v1.endpoints import (
    credit,
    documents,
    extraction,
    graph,
    health,
    omissions,
    resolution,
    unified,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(documents.router, tags=["Documents"])
api_router.include_router(extraction.router, tags=["Extraction"])
api_router.include_router(resolution.router, tags=["Resolution"])
api_router.include_router(graph.router, prefix="/graph", tags=["Knowledge Graph"])
api_router.include_router(omissions.router, tags=["Omission Detection"])
api_router.include_router(credit.router, tags=["Credit & Framing Analysis"])
api_router.include_router(unified.router, tags=["Unified Evidence Fusion & Scoring"])
