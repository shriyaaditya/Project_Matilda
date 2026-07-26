from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    app_name: str = Field(..., json_schema_extra={"example": "Project Matilda"})
    environment: str = Field(..., json_schema_extra={"example": "development"})
    version: str = Field(..., json_schema_extra={"example": "0.1.0"})
