import base64
from binascii import Error as Base64Error
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.api.contracts import AttachmentContext, AttachmentUploadRequest

router = APIRouter(tags=["assistant"])

MAX_ATTACHMENT_BYTES = 2_000_000
MAX_EXTRACTED_CHARACTERS = 6000
MAX_PDF_PAGES = 20
MEDIA_TYPE_BY_SUFFIX = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
}


def _decode_content(value: str) -> bytes:
    try:
        content = base64.b64decode(value, validate=True)
    except (Base64Error, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Attachment content must be valid base64.",
        ) from error
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Attachment is empty.",
        )
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Attachment exceeds the 2 MB limit.",
        )
    return content


def _extract_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Encrypted PDFs are not supported.",
            )
        if len(reader.pages) > MAX_PDF_PAGES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"PDF attachments are limited to {MAX_PDF_PAGES} pages.",
            )
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except (PdfReadError, OSError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The PDF could not be read.",
        ) from error


def _extract_text(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Text attachments must use UTF-8 encoding.",
        ) from error


@router.post("/attachments/extract", response_model=AttachmentContext)
async def extract_attachment(request: AttachmentUploadRequest) -> AttachmentContext:
    """Extract bounded user-provided text without storing the uploaded attachment."""
    suffix = Path(request.filename).suffix.casefold()
    expected_media_type = MEDIA_TYPE_BY_SUFFIX.get(suffix)
    if expected_media_type is None or request.media_type != expected_media_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only .txt, .md, and .pdf attachments are supported.",
        )

    content = _decode_content(request.content_base64)
    extracted = _extract_pdf(content) if suffix == ".pdf" else _extract_text(content)
    normalized = extracted.replace("\x00", "").strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No readable text was found in the attachment.",
        )

    truncated = len(normalized) > MAX_EXTRACTED_CHARACTERS
    return AttachmentContext(
        filename=request.filename,
        media_type=request.media_type,
        extracted_text=normalized[:MAX_EXTRACTED_CHARACTERS],
        original_size_bytes=len(content),
        truncated=truncated,
    )
