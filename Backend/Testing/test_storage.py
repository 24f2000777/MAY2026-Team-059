"""
Pytest suite for app/utils/storage.py.

No database needed, unlike most other suites here, these two
functions are pure content validation and a bounded async read, no
service layer or DB access involved.
"""

import io

import pytest
from fastapi import UploadFile

from app.core.config import settings
from app.utils.exceptions import FileTooLargeError, UnsupportedFileTypeError
from app.utils.storage import read_upload_bounded, validate_upload

JPEG_MAGIC_BYTES = b"\xff\xd8\xff" + b"fake-rest-of-file"
PNG_MAGIC_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-rest-of-file"
PDF_MAGIC_BYTES = b"%PDF-1.4\nfake-rest-of-file"


class TestValidateUpload:
    def test_accepts_real_jpeg_bytes(self):
        validate_upload("image/jpeg", JPEG_MAGIC_BYTES)

    def test_accepts_real_png_bytes(self):
        validate_upload("image/png", PNG_MAGIC_BYTES)

    def test_accepts_real_pdf_bytes(self):
        validate_upload("application/pdf", PDF_MAGIC_BYTES)

    def test_rejects_an_unsupported_content_type(self):
        with pytest.raises(UnsupportedFileTypeError):
            validate_upload("application/x-msdownload", JPEG_MAGIC_BYTES)

    def test_rejects_content_that_does_not_match_the_claimed_type(self):
        # Content-Type says JPEG, actual bytes are a PNG, the header
        # alone is never trusted.
        with pytest.raises(UnsupportedFileTypeError):
            validate_upload("image/jpeg", PNG_MAGIC_BYTES)

    def test_rejects_a_file_over_the_size_limit(self):
        oversized = JPEG_MAGIC_BYTES + b"x" * settings.MAX_UPLOAD_SIZE_BYTES

        with pytest.raises(FileTooLargeError):
            validate_upload("image/jpeg", oversized)

    def test_size_check_runs_before_the_signature_check(self):
        # An oversized file should fail as FileTooLargeError even if
        # its content wouldn't have matched the claimed type either,
        # size is checked first since it's the cheaper, more urgent
        # rejection (no point inspecting content that's already too
        # big to accept).
        oversized_and_wrong_content = b"not-a-real-jpeg" + b"x" * settings.MAX_UPLOAD_SIZE_BYTES

        with pytest.raises(FileTooLargeError):
            validate_upload("image/jpeg", oversized_and_wrong_content)


class TestReadUploadBounded:
    async def test_reads_the_whole_file_when_under_the_limit(self):
        data = JPEG_MAGIC_BYTES
        upload = UploadFile(file=io.BytesIO(data), filename="test.jpg")

        result = await read_upload_bounded(upload, max_size=settings.MAX_UPLOAD_SIZE_BYTES)

        assert result == data

    async def test_stops_reading_once_past_the_limit(self):
        # 3 MB of data, a 1 MB limit, the point of read_upload_bounded
        # is that it never buffers the whole 3 MB, only a little past
        # the 1 MB limit, so validate_upload can reject it as too
        # large without the full body ever having been read.
        max_size = 1024 * 1024
        data = b"x" * (3 * max_size)
        upload = UploadFile(file=io.BytesIO(data), filename="big.jpg")

        result = await read_upload_bounded(upload, max_size=max_size)

        assert len(result) > max_size
        assert len(result) < len(data)

    async def test_empty_file_reads_as_empty(self):
        upload = UploadFile(file=io.BytesIO(b""), filename="empty.jpg")

        result = await read_upload_bounded(upload, max_size=settings.MAX_UPLOAD_SIZE_BYTES)

        assert result == b""
