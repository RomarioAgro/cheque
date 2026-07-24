"""Tests for automatic T-Bank refund reference selection."""

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

_ORIGINAL_CWD = os.getcwd()
_ORIGINAL_ARGV = sys.argv
sys.argv = ["check.py", str(Path.cwd()), "test_tbank_refund"]
try:
    import check
finally:
    sys.argv = _ORIGINAL_ARGV
    os.chdir(_ORIGINAL_CWD)

from pinpad_tbank import OperationCode, TbankDC1


class TbankRefundLookupTest(unittest.TestCase):
    """Verify lookup integration without calling a real terminal."""

    @staticmethod
    def _receipt() -> dict:
        """Return minimal refund receipt data for the pinpad flow."""
        return {
            "PinPad": 1,
            "pinpad_type": "tbank",
            "operationtype": "return_sale",
            "sum-cashless": 100.0,
            "initial_sale_date": "24.07.26",
            "initial_sale_number": "377230/01",
        }

    def test_process_pinpad_passes_found_reference_number(self):
        """Pass a stored RRN to the terminal without changing the result."""
        client = Mock(error=0, text="receipt")
        client.pinpad_operation.return_value = SimpleNamespace(reference_number="620412740441")

        with patch.object(check, "safe_import", return_value=lambda: client), patch(
            "tbank_sql.find_tbank_refund_reference", return_value="620412740441"
        ):
            result = check._process_pinpad(SimpleNamespace(cash_receipt=self._receipt()))

        self.assertEqual(result, (0, "receipt"))
        client.pinpad_operation.assert_called_once_with(
            operation_name="return_sale",
            amount=100.0,
            reference_number="620412740441",
        )

    def test_process_pinpad_lookup_error_keeps_manual_fallback(self):
        """Pass ``None`` to the terminal when the database lookup fails."""
        client = Mock(error=0, text="receipt")
        client.pinpad_operation.return_value = SimpleNamespace(reference_number="manual")

        with patch.object(check, "safe_import", return_value=lambda: client), patch(
            "tbank_sql.find_tbank_refund_reference", side_effect=OSError("database unavailable")
        ):
            result = check._process_pinpad(SimpleNamespace(cash_receipt=self._receipt()))

        self.assertEqual(result, (0, "receipt"))
        client.pinpad_operation.assert_called_once_with(
            operation_name="return_sale",
            amount=100.0,
            reference_number=None,
        )

    def test_refund_skips_prompt_when_reference_is_provided(self):
        """Use a stored RRN without displaying the manual input dialog."""
        client = TbankDC1.__new__(TbankDC1)
        with patch.object(client, "_request_refund_rrn") as prompt, patch.object(
            client, "_financial_operation", return_value="result"
        ) as operation:
            result = client.refund(100.0, timeout_seconds=5, reference_number="620412740441")

        self.assertEqual(result, "result")
        prompt.assert_not_called()
        operation.assert_called_once_with(
            OperationCode.REFUND,
            100.0,
            5,
            reference_number="620412740441",
        )

    def test_refund_prompts_when_reference_is_missing(self):
        """Use the existing dialog when the database did not provide an RRN."""
        client = TbankDC1.__new__(TbankDC1)
        with patch.object(client, "_request_refund_rrn", return_value="manual") as prompt, patch.object(
            client, "_financial_operation", return_value="result"
        ) as operation:
            result = client.refund(100.0, timeout_seconds=5)

        self.assertEqual(result, "result")
        prompt.assert_called_once_with()
        operation.assert_called_once_with(
            OperationCode.REFUND,
            100.0,
            5,
            reference_number="manual",
        )


if __name__ == "__main__":
    unittest.main()
