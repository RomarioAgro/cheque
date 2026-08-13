import os
import sys
import unittest
from unittest.mock import patch


with patch.object(os, 'chdir'), patch.object(sys, 'argv', ['operation_shtrih.py', '.', 'test']):
    import operation_shtrih
    from operation_shtrih import open_shift


class FakeDriver:
    ResultCode = 0
    ResultCodeDescription = ''


class FakeShtrih:
    def __init__(self, modes, connect_error=0, open_error=None):
        self.modes = iter(modes)
        self.connect_error = connect_error
        self.open_error = open_error
        self.open_calls = 0
        self.drv = FakeDriver()

    def check_connect_fr(self):
        return self.connect_error, 'connection'

    def get_ecr_status(self):
        return next(self.modes), 'mode'

    def open_session(self):
        self.open_calls += 1
        if self.open_error:
            raise self.open_error


class OpenShiftTest(unittest.TestCase):
    def test_opens_closed_shift_once(self):
        shtrih = FakeShtrih([4, 2])
        self.assertEqual(open_shift(shtrih), 0)
        self.assertEqual(shtrih.open_calls, 1)

    def test_does_not_reopen_active_shift(self):
        shtrih = FakeShtrih([2])
        self.assertEqual(open_shift(shtrih), 0)
        self.assertEqual(shtrih.open_calls, 0)

    def test_returns_error_for_connection_or_invalid_mode(self):
        self.assertNotEqual(open_shift(FakeShtrih([], connect_error=5)), 0)
        self.assertNotEqual(open_shift(FakeShtrih([8])), 0)

    def test_returns_error_when_shift_does_not_open(self):
        self.assertNotEqual(open_shift(FakeShtrih([4, 4])), 0)

    def test_main_skips_print_setup_for_open_shift(self):
        shtrih = FakeShtrih([2])
        shtrih.print_on = lambda: self.fail('print_on must not run for open_shift')
        with patch.object(operation_shtrih, 'read_composition_receipt', return_value={'operationtype': 'open_shift'}), \
                patch.object(operation_shtrih, 'Shtrih', return_value=shtrih):
            self.assertEqual(operation_shtrih.main(), 0)


if __name__ == '__main__':
    unittest.main()
