import spacy
import spacy.cli


class PersonExtractor:
    def __init__(self, model_name: str = "en_core_web_sm") -> None:
        self.model_name = model_name
        try:
            self.nlp = spacy.load(model_name)
        except Exception:
            spacy.cli.download(model_name)  # type: ignore[attr-defined]
            self.nlp = spacy.load(model_name)

    def extract_person_mentions(self, sentence_text: str) -> list[tuple[str, str, int, int, None]]:
        """
        Extracts PERSON entities from a sentence text.
        Returns a list of tuples: (raw_text, normalized_text, start_char, end_char, confidence=None)
        """
        if not sentence_text.strip():
            return []

        doc = self.nlp(sentence_text)
        results: list[tuple[str, str, int, int, None]] = []

        for ent in doc.ents:
            if ent.label_ == "PERSON":
                raw_text = ent.text
                clean_raw = raw_text.strip()
                if not clean_raw:
                    continue

                # Preserve raw offsets in parent sentence
                start_char = ent.start_char
                end_char = ent.end_char
                normalized_text = clean_raw.lower()

                # Rule 1: Never store artificial confidence values (e.g. 1.0). Use None (NULL) when unexposed.
                confidence = None

                results.append((clean_raw, normalized_text, start_char, end_char, confidence))

        return results
