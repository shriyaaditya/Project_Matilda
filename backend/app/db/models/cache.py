from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, VARCHAR, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

JSONType = JSONB().with_variant(JSON(), "sqlite")


class WikidataCacheModel(Base):
    __tablename__ = "wikidata_cache"

    query_key: Mapped[str] = mapped_column(VARCHAR(256), primary_key=True)
    response_json: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
