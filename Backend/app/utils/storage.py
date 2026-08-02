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


def validate_upload(content_type: str, size_bytes: int) -> None:
    """
    Raises:
        UnsupportedFileTypeError: 415 (FILE_002), if content_type isn't
            one of ALLOWED_CONTENT_TYPES.
        FileTooLargeError: 413 (FILE_001), if size_bytes exceeds
            settings.MAX_UPLOAD_SIZE_BYTES.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{content_type}'. "
            f"Allowed: JPG, PNG, PDF, DOC, DOCX."
        )

    if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
        raise FileTooLargeError(f"File exceeds the {max_mb:.0f} MB limit.")


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
