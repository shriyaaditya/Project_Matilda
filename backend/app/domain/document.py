from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class Sentence(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    sentence_index: int = Field(..., description="0-indexed sentence order within paragraph")
    global_sentence_index: int = Field(..., description="0-indexed sentence order across entire document")
    text: str
    char_count: int


class Paragraph(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    paragraph_index: int = Field(..., description="0-indexed paragraph order within page")
    text: str
    bbox: BoundingBox | None = Field(None, description="Spatial layout coordinates (x0, y0, x1, y1)")
    sentences: list[Sentence] = Field(default_factory=list)


class Page(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    page_number: int = Field(..., description="1-indexed physical page number")
    has_extractable_text: bool = Field(True, description="False if page yields zero extractable text")
    raw_text: str
    paragraphs: list[Paragraph] = Field(default_factory=list)


class DocumentHeader(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    filename: str
    file_size_bytes: int
    sha256_hash: str
    file_path: str
    page_count: int
    status: str  # "PROCESSING", "COMPLETED", "FAILED", "NO_EXTRACTABLE_TEXT"
    is_duplicate: bool = Field(False, description="True if document matched an existing SHA-256 hash")
    error_message: str | None = None
    created_at: datetime


class DocumentStructured(DocumentHeader):
    pages: list[Page] = Field(default_factory=list)
