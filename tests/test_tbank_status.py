"""Tests for T-Bank transaction status handling."""

import unittest

from pinpad_tbank import OperationResult, TbankDC1


class TbankStatusTest(unittest.TestCase):
    """Verify that only an approved transaction is treated as successful."""

    @staticmethod
    def _result(exchange_result=0, status=None, text=None, host_code=None):
        """Build a minimal terminal response."""
        raw_response = {}
        if status is not None:
            raw_response["Status"] = status
        if text is not None:
            raw_response["TextResponse"] = text
        if host_code is not None:
            raw_response["ResponseCodeHost"] = host_code
        return OperationResult(exchange_result, {}, "", raw_response)

    def test_status_zero_card_read_error_is_not_success(self):
        """Do not fiscalize after the observed card-read failure response."""
        result = self._result(status="0", text="Ошибка чтения карты")

        self.assertNotEqual(TbankDC1._resolve_error_code(result), 0)

    def test_only_status_one_is_success(self):
        """Accept the documented approved status and preserve real errors."""
        self.assertEqual(TbankDC1._resolve_error_code(self._result(status="1")), 0)
        self.assertEqual(TbankDC1._resolve_error_code(self._result(status="16")), 16)
        self.assertNotEqual(TbankDC1._resolve_error_code(self._result(host_code="000")), 0)
        self.assertNotEqual(TbankDC1._resolve_error_code(self._result(5, status="1")), 0)


if __name__ == "__main__":
    unittest.main()
