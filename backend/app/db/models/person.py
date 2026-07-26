import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import INT, JSON, TEXT, VARCHAR, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.resolution import EntityResolutionModel

JSONType = JSONB().with_variant(JSON(), "sqlite")


class CanonicalPersonModel(Base):
    __tablename__ = "canonical_people"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    canonical_name: Mapped[str] = mapped_column(VARCHAR(512), nullable=False, index=True)
    wikidata_qid: Mapped[str | None] = mapped_column(
        VARCHAR(32), unique=True, index=True, nullable=True
    )
    birth_year: Mapped[int | None] = mapped_column(INT, nullable=True)
    death_year: Mapped[int | None] = mapped_column(INT, nullable=True)
    occupations: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    aliases: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    resolutions: Mapped[list["EntityResolutionModel"]] = relationship(
        "EntityResolutionModel", back_populates="person"
    )
