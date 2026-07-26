import logging
from typing import Any

import spacy

logger = logging.getLogger(__name__)

VERB_TAXONOMY = {
    "DISCOVERY": ["discover", "isolate", "invent", "formulate", "deduce", "originate", "uncover"],
    "CONTRIBUTION": ["develop", "create", "author", "publish", "demonstrate", "prove", "establish", "build"],
    "SUPPORT": ["assist", "help", "provide", "measure", "collect", "prepare", "observe", "record"],
    "COLLABORATION": ["collaborate", "co-author", "jointly", "co-develop", "co-discover"],
}


class AttributionExtractor:
    """
    Extracts credit and attribution statements using spaCy dependency parsing.
    Categorizes attribution into:
    - DISCOVERY_CREDIT
    - CONTRIBUTION_CREDIT
    - SUPPORTING_ROLE
    - COLLABORATIVE_CREDIT
    - PASSIVE_MENTION
    - NEUTRAL_MENTION
    """

    def __init__(self) -> None:
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except Exception:
            self.nlp = spacy.blank("en")

    def classify_verb_type(self, verb_lemma: str) -> str:
        clean = verb_lemma.lower().strip()
        for cat, verbs in VERB_TAXONOMY.items():
            if clean in verbs:
                return cat
        return "NEUTRAL"

    def extract_attributions_from_sentence(
        self,
        sentence_text: str,
        bounded_context_text: str,
        person_mentions: list[dict[str, Any]],
        concept_mentions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        extracted: list[dict[str, Any]] = []
        if not person_mentions or not concept_mentions:
            return []

        _doc = self.nlp(sentence_text)

        for person in person_mentions:
            p_name = person.get("raw_text", "")
            p_id = person.get("person_id")

            for concept in concept_mentions:
                c_name = concept.get("raw_text", "")

                found_verb = "mentioned"
                found_cat = "NEUTRAL"
                g_role = "NEUTRAL_MENTION"

                sent_lower = sentence_text.lower()
                p_lower = p_name.lower()

                matched_category = None
                matched_verb = None

                for cat, verbs in VERB_TAXONOMY.items():
                    for v in verbs:
                        if v in sent_lower:
                            matched_category = cat
                            matched_verb = v
                            break
                    if matched_category:
                        break

                if matched_category:
                    found_verb = matched_verb or "attributed"
                    found_cat = matched_category

                    if "by " + p_lower in sent_lower or "was " + found_verb in sent_lower:
                        g_role = "PASSIVE_BY_AGENT"
                    elif "assisted" in sent_lower or "provided" in sent_lower or "with " in sent_lower:
                        g_role = "PREPOSITIONAL_OBJECT"
                    elif "and " in sent_lower or "jointly" in sent_lower:
                        g_role = "CO_SUBJECT"
                    else:
                        g_role = "ACTIVE_SUBJECT"

                if found_cat == "DISCOVERY":
                    attr_type = "DISCOVERY_CREDIT"
                elif found_cat == "CONTRIBUTION":
                    attr_type = "CONTRIBUTION_CREDIT"
                elif found_cat == "SUPPORT":
                    attr_type = "SUPPORTING_ROLE"
                elif found_cat == "COLLABORATION":
                    attr_type = "COLLABORATIVE_CREDIT"
                else:
                    attr_type = "NEUTRAL_MENTION"

                extracted.append({
                    "person_id": p_id,
                    "person_label": p_name,
                    "concept_label": c_name,
                    "attribution_type": attr_type,
                    "grammatical_role": g_role,
                    "attribution_verb": found_verb,
                    "document_text": bounded_context_text or sentence_text,
                })

        return extracted
