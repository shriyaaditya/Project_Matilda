from fastapi import APIRouter

from app.api.v1.endpoints import documents, extraction, health, resolution

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(documents.router, tags=["Documents"])
api_router.include_router(extraction.router, tags=["Extraction"])
api_router.include_router(resolution.router, tags=["Resolution"])
