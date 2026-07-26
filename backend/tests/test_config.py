from app.core.config import Settings


def test_default_settings() -> None:
    settings = Settings()
    assert settings.APP_NAME == "Project Matilda"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.ENV in ["development", "testing", "production"]
    assert isinstance(settings.CORS_ORIGINS, list)


def test_cors_origins_parsing() -> None:
    s = Settings(CORS_ORIGINS="http://localhost:3000,http://localhost:8000")
    assert s.CORS_ORIGINS == ["http://localhost:3000", "http://localhost:8000"]
