"""
Local filesystem storage for complaint attachments.

Dev storage per Section 4 of the API design doc, prod is meant to be
S3-compatible object storage with signed URL expiry. Swapping this out
later is a matter of replacing save_attachment_file's body (write to
S3 instead of disk, return the object's URL instead of a local path),
callers here don't need to change, they just get back a URL string.
"""

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.utils.exceptions import FileTooLargeError, UnsupportedFileTypeError

# content type -> file extension. Deliberately not trusting the
# client-supplied filename's own extension, a malicious or just messy
# client could send "photo.jpg" with content_type "application/x-msdownload"
# or no extension at all, the extension actually written to disk is
# always derived from the validated content_type instead.
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

# The real leading bytes files of each allowed type start with, checked
# against the actual upload rather than trusting the client-supplied
# Content-Type header alone, a client could otherwise relabel arbitrary
# content as an allowed type and have it accepted. DOCX (like every
# OOXML format) is a ZIP container, this only confirms "is a ZIP", not
# "is specifically a Word document", full internal structure validation
# is more than this needs.
_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "application/pdf": (b"%PDF-",),
    "application/msword": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (b"PK\x03\x04",),
}


async def read_upload_bounded(file: UploadFile, max_size: int) -> bytes:
    """
    Reads an upload in chunks, stopping as soon as more than max_size
    bytes have come through, rather than file.read()'s default of
    buffering the entire body regardless of size first. Without this,
    a client sending a very large file still gets fully read (and
    spooled to disk by Starlette's UploadFile) before validate_upload
    ever gets a chance to reject it as too large, an easy memory/disk
    pressure vector. Reads at most one chunk past max_size, not
    however large the client actually sent.
    """
    chunk_size = 1024 * 1024
    chunks = []
    total = 0
    while total <= max_size:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


def validate_upload(content_type: str, file_bytes: bytes) -> None:
    """
    Raises:
        UnsupportedFileTypeError: 415 (FILE_002), if content_type isn't
            one of ALLOWED_CONTENT_TYPES, or file_bytes' actual leading
            bytes don't match what real files of that type start with.
        FileTooLargeError: 413 (FILE_001), if file_bytes exceeds
            settings.MAX_UPLOAD_SIZE_BYTES.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{content_type}'. "
            f"Allowed: JPG, PNG, PDF, DOC, DOCX."
        )

    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
        raise FileTooLargeError(f"File exceeds the {max_mb:.0f} MB limit.")

    signatures = _SIGNATURES[content_type]
    if not any(file_bytes.startswith(sig) for sig in signatures):
        raise UnsupportedFileTypeError(
            f"File content doesn't match the claimed type '{content_type}'."
        )


def save_attachment_file(complaint_id, content_type: str, file_bytes: bytes) -> str:
    """
    Writes file_bytes to UPLOAD_DIR/complaints/{complaint_id}/{uuid}.{ext}
    and returns the URL it's servable at (mounted in main.py).

    The filename on disk is always a fresh UUID, never anything
    derived from client input, so there's no path traversal surface
    and no collision risk between concurrent uploads.

    Does not validate, call validate_upload first, this only writes.
    """
    extension = ALLOWED_CONTENT_TYPES[content_type]
    directory = Path(settings.UPLOAD_DIR) / "complaints" / str(complaint_id)
    directory.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4()}{extension}"
    (directory / filename).write_bytes(file_bytes)

    return f"/{settings.UPLOAD_DIR}/complaints/{complaint_id}/{filename}"
