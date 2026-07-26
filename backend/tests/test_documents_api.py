import os

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.fixtures.pdf_fixtures import create_blank_pdf, create_sample_text_pdf


@pytest.mark.asyncio
async def test_upload_valid_pdf(async_client: AsyncClient) -> None:
    pdf_bytes = create_sample_text_pdf()
    files = {"file": ("physics_ch1.pdf", pdf_bytes, "application/pdf")}

    response = await async_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()

    assert data["filename"] == "physics_ch1.pdf"
    assert data["page_count"] == 2
    assert data["status"] == "COMPLETED"
    assert data["is_duplicate"] is False
    assert "id" in data
    assert "sha256_hash" in data
    assert "file_path" in data

    # Verification 1: Assert file actually exists in physical upload directory
    physical_file_path = data["file_path"]
    assert os.path.exists(physical_file_path)
    with open(physical_file_path, "rb") as f:
        stored_bytes = f.read()
    assert stored_bytes == pdf_bytes

    doc_id = data["id"]

    # Test GET /documents/{id}
    header_res = await async_client.get(f"/api/v1/documents/{doc_id}")
    assert header_res.status_code == 200
    assert header_res.json()["id"] == doc_id

    # Test GET /documents/{id}/structure
    struct_res = await async_client.get(f"/api/v1/documents/{doc_id}/structure")
    assert struct_res.status_code == 200
    struct_data = struct_res.json()
    assert len(struct_data["pages"]) == 2
    assert struct_data["pages"][0]["paragraphs"][0]["bbox"] is not None


@pytest.mark.asyncio
async def test_upload_duplicate_pdf(async_client: AsyncClient) -> None:
    pdf_bytes = create_sample_text_pdf()
    files1 = {"file": ("physics_ch1.pdf", pdf_bytes, "application/pdf")}
    files2 = {"file": ("physics_ch1_copy.pdf", pdf_bytes, "application/pdf")}

    # First upload -> 201 Created
    res1 = await async_client.post("/api/v1/documents/upload", files=files1)
    assert res1.status_code == 201
    d1 = res1.json()

    # Get count of files in upload directory after first upload
    upload_files_count_after_first = len(os.listdir(settings.UPLOAD_DIR))

    # Second upload with identical bytes -> 200 OK with is_duplicate = True
    res2 = await async_client.post("/api/v1/documents/upload", files=files2)
    assert res2.status_code == 200
    d2 = res2.json()

    assert d2["id"] == d1["id"]
    assert d2["is_duplicate"] is True

    # Verification 2: Assert duplicate upload did NOT create a new physical PDF file on disk
    upload_files_count_after_second = len(os.listdir(settings.UPLOAD_DIR))
    assert upload_files_count_after_first == upload_files_count_after_second


@pytest.mark.asyncio
async def test_upload_blank_pdf(async_client: AsyncClient) -> None:
    pdf_bytes = create_blank_pdf()
    files = {"file": ("empty.pdf", pdf_bytes, "application/pdf")}

    response = await async_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "NO_EXTRACTABLE_TEXT"


@pytest.mark.asyncio
async def test_upload_non_pdf_file(async_client: AsyncClient) -> None:
    files = {"file": ("test.txt", b"Hello world text file", "text/plain")}
    response = await async_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "Only .pdf files are accepted" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_upload_corrupt_pdf(async_client: AsyncClient) -> None:
    files = {"file": ("corrupt.pdf", b"NOT_A_REAL_PDF_HEADER", "application/pdf")}
    response = await async_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "Corrupt or unreadable PDF" in response.json()["error"]["message"]
