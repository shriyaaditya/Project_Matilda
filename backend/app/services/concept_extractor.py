import re

import spacy
import spacy.cli

from app.core.config import settings


class ConceptExtractor:
    def __init__(self, model_name: str = "en_core_web_sm") -> None:
        self.model_name = model_name
        try:
            self.nlp = spacy.load(model_name)
        except Exception:
            spacy.cli.download(model_name)  # type: ignore[attr-defined]
            self.nlp = spacy.load(model_name)

        self.noise_set: set[str] = {word.lower() for word in settings.CONCEPT_NOISE_WORDS}

    @staticmethod
    def _strip_leading_determiners(text: str, start_offset: int) -> tuple[str, int, int]:
        """Strips leading determiners ('the ', 'a ', 'an ') while updating start character offset correctly."""
        pattern = r"^(the|a|an|this|these|those|some)\s+"
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            matched_prefix = match.group(0)
            prefix_len = len(matched_prefix)
            cleaned_text = text[prefix_len:]
            new_start = start_offset + prefix_len
            return cleaned_text, new_start, new_start + len(cleaned_text)
        return text, start_offset, start_offset + len(text)

    def extract_concept_mentions(
        self, sentence_text: str, person_spans: list[tuple[int, int]] | None = None
    ) -> list[tuple[str, str, int, int, None]]:
        """
        Extracts CONCEPT entities dynamically using noun_chunks + POS rules.
        Filters out noise terms and candidate chunks overlapping with PERSON spans.
        Returns list of (raw_text, normalized_text, start_char, end_char, confidence=None)
        """
        if not sentence_text.strip():
            return []

        doc = self.nlp(sentence_text)
        results: list[tuple[str, str, int, int, None]] = []
        person_spans = person_spans or []

        for chunk in doc.noun_chunks:
            raw_chunk_text = chunk.text
            chunk_start = chunk.start_char

            # Clean leading determiners without breaking offset alignment
            clean_raw, start_char, end_char = self._strip_leading_determiners(raw_chunk_text, chunk_start)
            clean_raw = clean_raw.strip()

            if len(clean_raw) < 2:
                continue

            normalized_text = clean_raw.lower()

            # 1. Filter out generic noise terms & single numbers
            if normalized_text in self.noise_set or normalized_text.isdigit():
                continue

            # 2. Filter out pronouns / single character noise
            if any(tok.pos_ == "PRON" for tok in chunk):
                continue

            # 3. Rule 5: Ensure PERSON and CONCEPT extraction don't create overlapping duplicate mentions
            is_overlapping = False
            for p_start, p_end in person_spans:
                if max(start_char, p_start) < min(end_char, p_end):
                    is_overlapping = True
                    break

            if is_overlapping:
                continue

            # Rule 1: Confidence is explicitly None (NULL)
            confidence = None

            results.append((clean_raw, normalized_text, start_char, end_char, confidence))

        return results
