import re

import fitz
import pysbd

from app.domain.document import BoundingBox, Page, Paragraph, Sentence


class PDFParser:
    def __init__(self) -> None:
        self.segmenter = pysbd.Segmenter(language="en", clean=False)

    @staticmethod
    def normalize_text(text: str) -> str:
        # Fix hyphenation across line breaks (e.g. "in-\nteresting" -> "interesting")
        cleaned = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
        # Convert single newlines inside paragraph to space
        cleaned = re.sub(r"(?<!\n)\n(?!\n)", " ", cleaned)
        # Collapse multiple spaces
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        return cleaned.strip()

    @staticmethod
    def is_header_or_footer(bbox: tuple[float, float, float, float], page_height: float) -> bool:
        y0, y1 = bbox[1], bbox[3]
        return y1 <= page_height * 0.04 or y0 >= page_height * 0.96

    def parse_document(self, doc: fitz.Document) -> tuple[list[Page], str]:
        pages: list[Page] = []
        global_sentence_counter = 0
        total_extracted_chars = 0

        for page_idx in range(doc.page_count):
            fitz_page = doc.load_page(page_idx)
            page_height = fitz_page.rect.height
            page_number = page_idx + 1

            blocks = fitz_page.get_text("blocks")
            paragraphs: list[Paragraph] = []
            page_raw_text_parts: list[str] = []
            paragraph_counter = 0

            for b in blocks:
                # b tuple structure: (x0, y0, x1, y1, "text", block_no, block_type)
                block_type = b[6]
                if block_type != 0:  # Only process text blocks
                    continue

                raw_block_text = b[4]
                bbox_tuple = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))

                if self.is_header_or_footer(bbox_tuple, page_height):
                    continue

                normalized_para_text = self.normalize_text(raw_block_text)
                if not normalized_para_text:
                    continue

                page_raw_text_parts.append(normalized_para_text)
                total_extracted_chars += len(normalized_para_text)

                # Segment paragraph into sentences using pysbd
                raw_sentences = self.segmenter.segment(normalized_para_text)
                sentences: list[Sentence] = []

                for s_idx, s_text in enumerate(raw_sentences):
                    clean_s_text = s_text.strip()
                    if not clean_s_text:
                        continue
                    sentences.append(
                        Sentence(
                            sentence_index=s_idx,
                            global_sentence_index=global_sentence_counter,
                            text=clean_s_text,
                            char_count=len(clean_s_text),
                        )
                    )
                    global_sentence_counter += 1

                paragraphs.append(
                    Paragraph(
                        paragraph_index=paragraph_counter,
                        text=normalized_para_text,
                        bbox=BoundingBox(
                            x0=bbox_tuple[0],
                            y0=bbox_tuple[1],
                            x1=bbox_tuple[2],
                            y1=bbox_tuple[3],
                        ),
                        sentences=sentences,
                    )
                )
                paragraph_counter += 1

            page_raw_text = "\n\n".join(page_raw_text_parts)
            has_text = len(page_raw_text.strip()) > 0

            pages.append(
                Page(
                    page_number=page_number,
                    has_extractable_text=has_text,
                    raw_text=page_raw_text,
                    paragraphs=paragraphs,
                )
            )

        status = "COMPLETED" if total_extracted_chars > 0 else "NO_EXTRACTABLE_TEXT"
        return pages, status
