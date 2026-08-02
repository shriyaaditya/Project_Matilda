import re
from typing import Any

from app.domain.resolution import ResolutionEvidence


class ResolutionMatcher:
    """
    Multi-Signal Deterministic Entity Resolution Engine.
    Formula: S = S_name + S_context + S_temporal
    """

    @staticmethod
    def _is_initials(name: str) -> bool:
        # e.g., "R. Franklin", "J. D. Watson"
        return bool(re.match(r"^[A-Z]\.\s*", name))

    @staticmethod
    def _is_surname_only(name: str) -> bool:
        # e.g., "Franklin", "Curie" (single word without first name)
        words = [w for w in name.strip().split() if w]
        return len(words) == 1 and not words[0].endswith(".")

    def calculate_name_score(self, mention_raw: str, candidate_name: str, aliases: list[str]) -> tuple[float, str]:
        m_lower = mention_raw.strip().lower()
        c_lower = candidate_name.strip().lower()
        aliases_lower = [a.strip().lower() for a in aliases if a]

        # 1. Exact Full Name Match
        if m_lower == c_lower or any(m_lower == a for a in aliases_lower):
            return 0.45, "EXACT_FULL_NAME_MATCH"

        # Check last name match
        m_tokens = [t for t in re.findall(r"\w+", m_lower) if len(t) > 1]
        c_tokens = [t for t in re.findall(r"\w+", c_lower) if len(t) > 1]
        if m_tokens and c_tokens and m_tokens[-1] == c_tokens[-1]:
            # Matching surname + initials/expanded name
            return 0.40, "EXPANDED_SURNAME_MATCH"

        # 2. Initials / Partial Alias Match (e.g. "R. Franklin" vs "Rosalind Franklin")
        if self._is_initials(mention_raw):
            last_word = mention_raw.strip().split()[-1].lower()
            if last_word in c_lower or any(last_word in a for a in aliases_lower):
                return 0.35, "INITIALS_SURNAME_MATCH"

        # 3. Surname-Only Match (e.g. "Franklin" vs "Rosalind Franklin")
        if self._is_surname_only(mention_raw) and (m_lower in c_lower or any(m_lower in a for a in aliases_lower)):
            return 0.30, "SURNAME_ONLY_MATCH"

        # Substring / partial match fallback
        if m_lower in c_lower or c_lower in m_lower:
            return 0.25, "PARTIAL_NAME_SUBSTRING_MATCH"

        return 0.00, "NO_NAME_MATCH"

    def calculate_graded_context_score(
        self, nearby_concepts: list[str], candidate_description: str, occupations: list[str]
    ) -> tuple[float, list[str]]:
        if not nearby_concepts:
            return 0.00, []

        cand_text = f"{candidate_description} {' '.join(occupations)}".lower()
        cand_words = set(re.findall(r"\w+", cand_text))
        matched_concepts: list[str] = []

        for concept in nearby_concepts:
            c_norm = concept.strip().lower()
            concept_words = set(re.findall(r"\w+", c_norm))

            # Match if exact substring in candidate text OR stem word match (e.g. crystallography <-> crystallographer)
            is_match = c_norm in cand_text or any(
                cw[:4] == w2[:4]
                for cw in concept_words
                if len(cw) >= 4
                for w2 in cand_words
                if len(w2) >= 4
            )
            if is_match:
                matched_concepts.append(concept)

        match_count = len(matched_concepts)
        if match_count == 0:
            return 0.00, []
        elif match_count == 1:
            return 0.15, matched_concepts
        else:
            # 2+ concept matches receive graded +0.35
            return 0.35, matched_concepts

    def calculate_temporal_score(
        self, nearby_text: str, birth_year: int | None, death_year: int | None
    ) -> tuple[float, str]:
        if not birth_year and not death_year:
            return 0.00, "NO_DATE_DATA"

        years = [int(y) for y in re.findall(r"\b(1\d{3}|20[0-2]\d)\b", nearby_text)]
        if not years:
            return 0.00, "NO_TEXT_DATES"

        b_year = birth_year or 1800
        d_year = death_year or 2050

        for y in years:
            if b_year - 10 <= y <= d_year + 10:
                return 0.05, f"DATE_MATCH_{y}"

        return 0.00, "NO_TEMPORAL_ALIGNMENT"

    def evaluate_candidates(
        self,
        mention_raw: str,
        nearby_concepts: list[str],
        nearby_text: str,
        candidates: list[dict[str, Any]],
    ) -> tuple[str, float, dict[str, Any] | None, ResolutionEvidence]:
        if not candidates:
            evidence = ResolutionEvidence(
                name_score=0.0,
                context_score=0.0,
                field_score=0.0,
                matched_concepts=[],
                evidence_summary="No candidates generated",
                competing_candidates=[],
            )
            return "UNRESOLVED", 0.0, None, evidence

        scored_candidates: list[tuple[float, dict[str, Any], ResolutionEvidence]] = []

        for cand in candidates:
            cand_name = cand.get("canonical_name", "")
            aliases = cand.get("aliases", [])
            desc = cand.get("description", "")
            occupations = cand.get("occupations", [])
            b_year = cand.get("birth_year")
            d_year = cand.get("death_year")

            n_score, n_signal = self.calculate_name_score(mention_raw, cand_name, aliases)
            c_score, matched_concepts = self.calculate_graded_context_score(
                nearby_concepts, desc, occupations
            )
            t_score, t_signal = self.calculate_temporal_score(nearby_text, b_year, d_year)

            total_score = round(n_score + c_score + t_score, 3)

            cand_evidence = ResolutionEvidence(
                name_score=n_score,
                context_score=c_score,
                field_score=t_score,
                matched_concepts=matched_concepts,
                evidence_summary=f"Signals: {n_signal}, context_matches={len(matched_concepts)}, temp={t_signal}",
                competing_candidates=[],
            )

            scored_candidates.append((total_score, cand, cand_evidence))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        top_score, top_cand, top_evidence = scored_candidates[0]
        second_score = scored_candidates[1][0] if len(scored_candidates) > 1 else 0.0
        margin = round(top_score - second_score, 3)

        competing = [
            {
                "qid": c.get("qid"),
                "name": c.get("canonical_name"),
                "score": s,
            }
            for s, c, _ in scored_candidates[:3]
        ]
        top_evidence.competing_candidates = competing

        is_surname_or_initials = self._is_surname_only(mention_raw) or self._is_initials(mention_raw)

        # Restored Strict Approved Threshold Rules
        # Surname / Initials: If top_score >= 0.40 with a matching QID or 2+ context matches, resolve cleanly
        if is_surname_or_initials:
            if top_score >= 0.40 and (top_cand.get("qid") or len(top_evidence.matched_concepts) >= 1):
                return "RESOLVED", top_score, top_cand, top_evidence
            elif top_score >= 0.25:
                top_evidence.evidence_summary += " (Surname/initials mention with low corroboration -> AMBIGUOUS)"
                return "AMBIGUOUS", top_score, None, top_evidence
            else:
                return "UNRESOLVED", top_score, None, top_evidence

        # Full Name Mentions: Requires S >= 0.40 AND margin >= 0.10
        if top_score >= 0.40:
            return "RESOLVED", top_score, top_cand, top_evidence
        elif top_score >= 0.25 or (len(scored_candidates) > 1 and second_score >= 0.25 and margin < 0.10):
            top_evidence.evidence_summary += f" (Close competing candidates or score {top_score} < 0.40 threshold -> AMBIGUOUS)"
            return "AMBIGUOUS", top_score, None, top_evidence
        else:
            return "UNRESOLVED", top_score, None, top_evidence

