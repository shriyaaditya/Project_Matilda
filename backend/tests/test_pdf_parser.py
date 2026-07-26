import fitz

from app.services.pdf_parser import PDFParser
from tests.fixtures.pdf_fixtures import create_blank_pdf, create_sample_text_pdf


def test_pdf_parser_sample_text() -> None:
    pdf_bytes = create_sample_text_pdf()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parser = PDFParser()

    pages, status = parser.parse_document(doc)

    assert status == "COMPLETED"
    assert len(pages) == 2

    # Page 1 checks
    page1 = pages[0]
    assert page1.page_number == 1
    assert page1.has_extractable_text is True
    assert len(page1.paragraphs) > 0

    first_para = page1.paragraphs[0]
    assert first_para.bbox is not None
    assert first_para.bbox.x0 >= 0
    assert len(first_para.sentences) > 0

    # Verify sentence global order sequence
    all_sentences = [s for p in pages for para in p.paragraphs for s in para.sentences]
    for idx, sentence in enumerate(all_sentences):
        assert sentence.global_sentence_index == idx


def test_pdf_parser_blank_pdf() -> None:
    pdf_bytes = create_blank_pdf()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parser = PDFParser()

    pages, status = parser.parse_document(doc)

    assert status == "NO_EXTRACTABLE_TEXT"
    assert len(pages) == 1
    assert pages[0].has_extractable_text is False
    assert len(pages[0].paragraphs) == 0
