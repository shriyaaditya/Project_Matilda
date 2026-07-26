from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Mention(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    sentence_id: UUID
    page_number: int
    paragraph_index: int
    sentence_index: int
    mention_type: str  # "PERSON" or "CONCEPT"
    raw_text: str = Field(..., description="Exact unmutated text extracted from sentence source")
    normalized_text: str = Field(..., description="Lowercased/trimmed text for search indexing")
    start_char: int = Field(..., description="0-indexed start offset within parent sentence text")
    end_char: int = Field(..., description="0-indexed end offset within parent sentence text")
    confidence: float | None = Field(None, description="Model confidence score if exposed; NULL if unexposed")
    extraction_method: str = Field(..., description="Extraction algorithm (e.g. 'SPACY_NER', 'NOUN_CHUNK_FILTER')")
    model_version: str = Field(..., description="Model version string (e.g. 'en_core_web_sm')")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExtractionSummary(BaseModel):
    document_id: UUID
    total_sentences_processed: int
    person_mentions_count: int
    concept_mentions_count: int
    is_already_extracted: bool
