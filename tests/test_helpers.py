"""Tests for product warranty date calculations."""

import unittest
import json
from datetime import date
from io import BytesIO
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory

_helper_path = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "product_warranty"
    / "helpers.py"
)
_helper_spec = spec_from_file_location("product_warranty_helpers", _helper_path)
if _helper_spec is None or _helper_spec.loader is None:
    raise RuntimeError(f"Unable to load warranty helper at {_helper_path}")
_helpers = module_from_spec(_helper_spec)
_helper_spec.loader.exec_module(_helpers)
warranty_end_date = _helpers.warranty_end_date
receipt_file_path = _helpers.receipt_file_path
store_receipt = _helpers.store_receipt


class WarrantyEndDateTests(unittest.TestCase):
    """Test calendar-month warranty expiry calculations."""

    def test_clamps_to_last_day_of_shorter_month(self) -> None:
        self.assertEqual(
            date(2025, 2, 28), warranty_end_date(date(2025, 1, 31), 1)
        )

    def test_leap_day_anniversary_clamps_in_non_leap_year(self) -> None:
        self.assertEqual(
            date(2025, 2, 28), warranty_end_date(date(2024, 2, 29), 12)
        )

    def test_preserves_day_when_present(self) -> None:
        self.assertEqual(
            date(2025, 8, 15), warranty_end_date(date(2025, 2, 15), 6)
        )

    def test_receipt_file_and_product_metadata_survive_reload(self) -> None:
        receipt_bytes = b"%PDF-1.7\nreceipt contents"
        with TemporaryDirectory() as temp_dir:
            storage_dir = Path(temp_dir) / "product_warranty" / "entry-123"
            receipt = store_receipt(
                storage_dir,
                BytesIO(receipt_bytes),
                "purchase-receipt.pdf",
                "application/pdf",
            )
            saved_options = json.dumps({"receipt": receipt})

            reloaded_options = json.loads(saved_options)
            self.assertEqual(
                "purchase-receipt.pdf", reloaded_options["receipt"]["filename"]
            )
            self.assertEqual(
                receipt_bytes, receipt_file_path(storage_dir).read_bytes()
            )


if __name__ == "__main__":
    unittest.main()
