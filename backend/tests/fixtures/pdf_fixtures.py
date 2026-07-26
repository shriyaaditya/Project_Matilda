import io

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_sample_text_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # Page 1
    c.drawString(100, 700, "Historical Physics Textbook - Chapter 1.")
    c.drawString(
        100,
        680,
        "Dr. Chien-Shiung Wu conducted the landmark parity experiment in c. 1956.",
    )
    c.drawString(
        100,
        660,
        "Her work disproved the law of conservation of parity in weak nuclear interactions.",
    )
    c.showPage()

    # Page 2
    c.drawString(100, 700, "Chapter 2: Contribution Attribution and Erasure.")
    c.drawString(
        100,
        680,
        "Lise Meitner played a pivotal role in the discovery of nuclear fission.",
    )
    c.showPage()

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def create_blank_pdf() -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.showPage()  # Empty page with 0 text elements
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
