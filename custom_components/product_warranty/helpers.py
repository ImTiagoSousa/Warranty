"""Date helpers for product warranties."""

import re
import shutil
from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

MAX_RECEIPT_SIZE = 10 * 1024 * 1024
_RECEIPT_TYPES = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
}


class InvalidReceipt(ValueError):
    """Raised when an uploaded receipt is unsupported or invalid."""


def warranty_end_date(purchase_date: date, duration_months: int) -> date:
    """Return the date the warranty ends, clamping to the month's last day."""
    month_index = purchase_date.month - 1 + duration_months
    year = purchase_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(purchase_date.day, monthrange(year, month)[1])
    return date(year, month, day)


def receipt_file_path(storage_dir: str | Path) -> Path:
    """Return the private storage path for a product's receipt."""
    return Path(storage_dir) / "receipt"


def store_receipt(
    storage_dir: str | Path,
    uploaded_file: BinaryIO,
    filename: str,
    content_type: str | None,
) -> dict[str, str | int]:
    """Validate and atomically store one uploaded receipt."""
    extension = Path(filename.replace("\\", "/")).suffix.lower()
    receipt_type = _RECEIPT_TYPES.get(extension)
    if receipt_type is None:
        raise InvalidReceipt("Use a PDF, PNG, or JPEG receipt.")

    expected_type, signature = receipt_type
    if content_type not in (None, "", "application/octet-stream", expected_type):
        raise InvalidReceipt("The file type does not match its filename.")

    uploaded_file.seek(0, 2)
    size = uploaded_file.tell()
    uploaded_file.seek(0)
    if size == 0:
        raise InvalidReceipt("The receipt file is empty.")
    if size > MAX_RECEIPT_SIZE:
        raise InvalidReceipt("Receipt files must be 10 MB or smaller.")
    if uploaded_file.read(len(signature)) != signature:
        raise InvalidReceipt("The file contents do not match a supported receipt.")
    uploaded_file.seek(0)

    safe_filename = Path(filename.replace("\\", "/")).name
    safe_filename = re.sub(r"[\x00-\x1f\x7f]", "", safe_filename)[:128]
    if not safe_filename:
        safe_filename = f"receipt{extension}"

    directory = Path(storage_dir)
    directory.mkdir(parents=True, exist_ok=True)
    temporary_path = directory / f".receipt-{uuid4().hex}.tmp"
    destination = receipt_file_path(directory)
    try:
        with temporary_path.open("xb") as target:
            shutil.copyfileobj(uploaded_file, target)
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)

    return {
        "filename": safe_filename,
        "extension": extension,
        "content_type": expected_type,
        "size": size,
    }
