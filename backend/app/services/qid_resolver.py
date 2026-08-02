import logging
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.wikidata_service import WikidataService

logger = logging.getLogger(__name__)

FIELD_SYNONYM_STEMS = {
    "physics": ["phys", "nuc", "atom", "quantum", "opt", "astro"],
    "chemistry": ["chem", "cryst", "mat", "microscop", "pharm", "bioch"],
    "biology": ["bio", "genet", "botan", "physiol", "microb", "zoolog", "med"],
    "mathematics": ["math", "stat", "algeb", "topol", "comput"],
    "astronomy": ["astro", "cosmo", "space", "planet"],
    "computer science": ["comput", "softw", "inform", "program", "cyber", "engine"],
    "engineering": ["engin", "mechan", "electr", "aero", "techno", "architect"],
    "medicine": ["med", "physic", "pharm", "epidemi", "pathol", "health", "oncolog"],
    "geology": ["geol", "ocean", "cartog", "seism", "earth", "paleo", "palaeo"],
    "paleontology": ["paleo", "palaeo", "fossil", "dinosau"],
}

NON_HUMAN_SUFFIXES = [
    " award", " prize", " medal", " scholarship", " street", " straße",
    " road", " avenue", " building", " hall", " institute", " college",
    " school", " university", " foundation", " movement", " comic",
    " film", " movie", " painting", " portrait", " article", " dissertation",
    " crater", " asteroid", " satellite", " ship", " vessel", " disambiguation",
]


class QIDResolver:
    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db
        self.wikidata_service = WikidataService(db)

    def _strip_titles(self, label: str) -> str:
        clean = re.sub(r"^(dr\.|doctor|sister|prof\.|professor|countess)\s+", "", label, flags=re.IGNORECASE)
        clean = re.sub(r"\s+\(.*\)$", "", clean)
        return clean.strip()

    def _is_non_human(self, name: str, desc: str) -> bool:
        combined = f"{name} {desc}".lower()
        return any(suffix in combined for suffix in NON_HUMAN_SUFFIXES)

    async def resolve_person_qid(
        self, label: str, properties: dict[str, Any]
    ) -> tuple[str | None, str, float, list[dict[str, Any]]]:
        """
        Resolves Wikidata QID for a PERSON record using multi-attribute search and validation.
        Returns: (resolved_qid, verification_status, confidence_score, candidates_evaluated)
        """
        search_queries = [label]
        stripped = self._strip_titles(label)
        if stripped != label:
            search_queries.append(stripped)

        # Handle hyphenated / compound names (e.g., Cecilia Payne-Gaposchkin -> Cecilia Payne)
        if "-" in stripped:
            search_queries.append(stripped.replace("-", " "))

        all_candidates: list[dict[str, Any]] = []
        seen_qids: set[str] = set()

        for q in search_queries:
            results = await self.wikidata_service.search_entities(q, limit=5)
            for cand in results:
                qid = cand.get("qid")
                if qid and qid not in seen_qids:
                    seen_qids.add(qid)
                    all_candidates.append(cand)

        if not all_candidates:
            return None, "PENDING_WIKIDATA_VERIFICATION", 0.0, []

        evaluated_candidates: list[dict[str, Any]] = []
        best_cand: dict[str, Any] | None = None
        best_score = 0.0

        primary_field = (properties.get("primary_field") or "").lower()
        country = (properties.get("country") or "").lower()

        for cand in all_candidates:
            cand_name = cand.get("canonical_name", "").lower()
            desc = (cand.get("description") or "").lower()
            occupations = [o.lower() for o in cand.get("occupations", [])]

            # Skip non-human items (awards, streets, scholarly articles, comics, ships)
            if self._is_non_human(cand_name, desc):
                continue

            cand_text = f"{desc} {' '.join(occupations)}"
            cand_words = set(re.findall(r"\w+", cand_text))

            # 1. Name Score
            n_score = 0.0
            clean_label = label.strip().lower()
            clean_stripped = stripped.lower()

            if clean_label == cand_name or clean_stripped == cand_name:
                n_score = 0.75  # Exact human name match
            elif clean_label in cand_name or cand_name in clean_label or clean_stripped in cand_name:
                n_score = 0.50
            else:
                # Name word overlap check
                l_words = set(re.findall(r"\w+", clean_stripped))
                c_words = set(re.findall(r"\w+", cand_name))
                overlap = l_words.intersection(c_words)
                if len(overlap) >= 2 or (len(l_words) == 1 and len(overlap) == 1):
                    n_score = 0.40

            # 2. Field / Occupation Score with stem & synonym matching
            f_score = 0.0
            if primary_field:
                field_stems: set[str] = set()
                for pf_key, stems in FIELD_SYNONYM_STEMS.items():
                    if pf_key in primary_field:
                        field_stems.update(stems)
                for w in re.findall(r"\w+", primary_field):
                    if len(w) >= 4:
                        field_stems.add(w[:4])

                if any(
                    stem in w2[:len(stem)] or w2[:len(stem)] in stem
                    for stem in field_stems
                    for w2 in cand_words
                    if len(w2) >= 3
                ):
                    f_score = 0.15

            # 3. Country / Region Score with prefix stem matching
            c_score = 0.0
            if country:
                country_words = [w for w in re.findall(r"\w+", country) if len(w) >= 4]
                if any(
                    cw[:4] in w2[:4] or w2[:4] in cw[:4]
                    for cw in country_words
                    for w2 in cand_words
                    if len(w2) >= 4
                ):
                    c_score = 0.10

            total_score = round(min(1.0, n_score + f_score + c_score), 2)
            evaluated_candidates.append({
                "qid": cand.get("qid"),
                "canonical_name": cand.get("canonical_name"),
                "score": total_score,
                "description": cand.get("description"),
            })

            if total_score > best_score:
                best_score = total_score
                best_cand = cand

        # Minimum confidence threshold 0.70 for automatic resolution
        if best_cand and best_score >= 0.70:
            return best_cand.get("qid"), "QID_VERIFIED", best_score, evaluated_candidates

        return None, "PENDING_WIKIDATA_VERIFICATION", best_score, evaluated_candidates
