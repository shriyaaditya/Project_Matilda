import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class SourceDeduplicator:
    """
    Normalizes DOIs, URIs, and Wikidata source IDs to prevent double-counting duplicated evidence items.
    """

    @staticmethod
    def normalize_doi(uri_or_doi: str) -> str:
        clean = uri_or_doi.strip().lower()
        # Extract standard 10.xxxx/yyyy DOI format
        match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", clean)
        if match:
            return match.group(0).strip("/")
        return clean

    def deduplicate_evidence_sources(
        self, raw_sources: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        seen_keys: set[str] = set()
        unique_sources: list[dict[str, Any]] = []
        dedup_log: list[str] = []

        for source in raw_sources:
            uri = source.get("source_uri") or source.get("doi") or source.get("reference_text", "")
            norm_key = self.normalize_doi(uri)

            if not norm_key:
                unique_sources.append(source)
                continue

            if norm_key in seen_keys:
                dedup_log.append(f"Deduplicated duplicate source record for URI '{uri}' (Key: '{norm_key}')")
            else:
                seen_keys.add(norm_key)
                unique_sources.append(source)

        return unique_sources, dedup_log
