from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Project Matilda"
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    VERSION: str = "0.1.0"

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("["):
                import json
                try:
                    return json.loads(v_str)
                except Exception:
                    pass
            return [i.strip() for i in v_str.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Document Upload & Local Storage Settings
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_MIME_TYPES: list[str] = ["application/pdf"]
    UPLOAD_DIR: str = "storage/uploads"

    # Calibrated Pipeline Thresholds (Phase 8 Calibration)
    COVERAGE_THRESHOLD: float = 0.60
    OMISSION_THRESHOLD: float = 0.50
    CREDIT_DISCREPANCY_THRESHOLD: float = 0.50

    # Concept Extraction Noise Filter (Configurable list of generic textbook filler terms)
    CONCEPT_NOISE_WORDS: list[str] = [
        "chapter",
        "page",
        "figure",
        "table",
        "section",
        "book",
        "textbook",
        "method",
        "author",
        "experiment",
        "result",
        "example",
        "percent",
        "unit",
        "value",
        "study",
        "work",
        "data",
        "analysis",
    ]

    # PostgreSQL Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "matilda_db"

    # Phase 9 LLM Reasoning & Explanation Configuration
    LLM_PROVIDER: str = "mock"  # "mock" | "openai" | "gemini"
    LLM_MODEL: str = "gemini-3.5-flash"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_TIMEOUT_SECONDS: float = 15.0
    LLM_MAX_RETRIES: int = 2
    LLM_REASONING_ENABLED: bool = False
    LLM_EXPLANATION_ENABLED: bool = False
    LLM_CACHE_ENABLED: bool = True

    @property
    def ASYNC_DATABASE_URI(self) -> str:
        from urllib.parse import quote_plus

        encoded_password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{encoded_password}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
