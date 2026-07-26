from app.db.models.cache import WikidataCacheModel
from app.db.models.document import DocumentModel, PageModel, ParagraphModel, SentenceModel
from app.db.models.mention import MentionModel
from app.db.models.person import CanonicalPersonModel
from app.db.models.resolution import EntityResolutionModel

__all__ = [
    "DocumentModel",
    "PageModel",
    "ParagraphModel",
    "SentenceModel",
    "MentionModel",
    "CanonicalPersonModel",
    "EntityResolutionModel",
    "WikidataCacheModel",
]
