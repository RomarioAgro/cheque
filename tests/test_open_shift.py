import os
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch


with patch.object(os, 'chdir'), patch.object(sys, 'argv', ['operation_shtrih.py', '.', 'test']):
    import operation_shtrih
    from operation_shtrih import ask_cashier_code, find_cashier, get_cashier, open_shift, show_shift_error, update_cashiers


class FakeDriver:
    ResultCode = 0
    ResultCodeDescription = ''
    INN = '1234567890'

    def FNGetFiscalizationResult(self):
        pass


class FakeShtrih:
    def __init__(self, modes, connect_error=0, open_error=None, inn='1234567890'):
        self.modes = iter(modes)
        self.connect_error = connect_error
        self.open_error = open_error
        self.open_calls = 0
        self.drv = FakeDriver()
        self.drv.INN = inn
        self.cash_receipt = {}

    def check_connect_fr(self):
        return self.connect_error, 'connection'

    def get_ecr_status(self):
        return next(self.modes), 'mode'

    def open_session(self):
        self.open_calls += 1
        self.tags_at_open = dict(self.cash_receipt)
        if self.open_error:
            raise self.open_error


class OpenShiftTest(unittest.TestCase):
    def setUp(self):
        self.real_show_shift_error = show_shift_error
        self.show_error_patcher = patch.object(operation_shtrih, 'show_shift_error')
        self.show_error = self.show_error_patcher.start()
        self.addCleanup(self.show_error_patcher.stop)

    def test_shtrih_can_skip_json_receipt(self):
        with patch.object(operation_shtrih.Shtrih, 'make_dict_receipt') as make_receipt, \
                patch.object(operation_shtrih.Shtrih, 'make_com_object_progid', return_value=object()):
            shtrih = operation_shtrih.Shtrih(load_receipt=False)
            self.assertEqual(shtrih.cash_receipt, {})
            make_receipt.assert_not_called()

        with patch.object(operation_shtrih.Shtrih, 'make_dict_receipt', return_value={'operationtype': 'sale'}) as make_receipt, \
                patch.object(operation_shtrih.Shtrih, 'make_com_object_progid', return_value=object()):
            shtrih = operation_shtrih.Shtrih('path', 'receipt')
            self.assertEqual(shtrih.cash_receipt, {'operationtype': 'sale'})
            make_receipt.assert_called_once_with(i_path='path', i_file_name='receipt')

    def test_main_open_shift_cli_does_not_read_json(self):
        shtrih = FakeShtrih([2])
        with patch.object(operation_shtrih, 'OPEN_SHIFT_CLI', True), \
                patch.object(operation_shtrih, 'read_composition_receipt') as read_json, \
                patch.object(operation_shtrih, 'Shtrih', return_value=shtrih) as shtrih_class:
            self.assertEqual(operation_shtrih.main(), 0)
            read_json.assert_not_called()
            shtrih_class.assert_called_once_with(load_receipt=False)

    def test_gui_cashier_code_success_and_cancel(self):
        root = unittest.mock.MagicMock()
        dialog = unittest.mock.MagicMock()
        with patch.object(tk, 'Tk', return_value=root):
            dialog.return_value.result = '  007  '
            self.assertEqual(ask_cashier_code(dialog), '007')
            root.withdraw.assert_called_once()
            root.destroy.assert_called_once()

            root.reset_mock()
            dialog.return_value.result = None
            self.assertIsNone(ask_cashier_code(dialog))
            root.destroy.assert_called_once()

            root.reset_mock()
            root.withdraw.side_effect = RuntimeError
            with self.assertRaises(RuntimeError):
                ask_cashier_code(dialog)
            root.destroy.assert_called_once()

    def test_empty_gui_cashier_code_blocks_lookup(self):
        with patch.object(operation_shtrih, 'update_cashiers'), \
                patch.object(operation_shtrih, 'ask_cashier_code', return_value=''), \
                patch.object(operation_shtrih, 'find_cashier') as find:
            with self.assertRaises(ValueError):
                get_cashier()
            find.assert_not_called()

    def test_gui_error_returns_nonzero_from_open_shift(self):
        with patch.object(operation_shtrih, 'get_cashier', side_effect=tk.TclError):
            self.assertNotEqual(open_shift(FakeShtrih([4])), 0)
        self.show_error.assert_called_with(
            'Ошибка открытия смены', 'Не удалось открыть смену. Подробности записаны в журнал.')

    def test_cashier_error_shows_safe_gui_message(self):
        with patch.object(operation_shtrih, 'get_cashier', side_effect=ValueError('кассир не найден')):
            self.assertNotEqual(open_shift(FakeShtrih([4])), 0)
        self.show_error.assert_called_once_with('Ошибка кассира', 'кассир не найден')

    def test_shift_error_dialog_is_topmost_and_safe_on_failure(self):
        root = unittest.mock.MagicMock()
        with patch.object(tk, 'Tk', return_value=root), patch('tkinter.messagebox.showerror') as message:
            self.real_show_shift_error('Ошибка', 'Понятная причина')
            root.attributes.assert_called_once_with('-topmost', True)
            message.assert_called_once_with('Ошибка', 'Понятная причина', parent=root)
            root.destroy.assert_called_once()

        root.reset_mock()
        with patch.object(tk, 'Tk', return_value=root), \
                patch('tkinter.messagebox.showerror', side_effect=RuntimeError('secret')), \
                patch.object(operation_shtrih.logger_operation_shtrih, 'warning') as warning:
            self.real_show_shift_error('Ошибка', 'Понятная причина')
            self.assertNotIn('secret', str(warning.call_args))
            root.destroy.assert_called_once()

    def test_dialog_destroy_failure_preserves_device_error_code(self):
        root = unittest.mock.MagicMock()
        root.destroy.side_effect = RuntimeError('secret')
        with patch.object(operation_shtrih, 'show_shift_error', self.real_show_shift_error), \
                patch.object(tk, 'Tk', return_value=root), \
                patch('tkinter.messagebox.showerror'), \
                patch.object(operation_shtrih.logger_operation_shtrih, 'warning') as warning:
            self.assertEqual(open_shift(FakeShtrih([], connect_error=5)), 5)
            self.assertNotIn('secret', str(warning.call_args))

    def test_opens_closed_shift_once(self):
        shtrih = FakeShtrih([4, 2])
        with patch.object(operation_shtrih, 'get_cashier', return_value=('Иванов Иван', '123456789012', '1234567890')):
            self.assertEqual(open_shift(shtrih), 0)
        self.assertEqual(shtrih.open_calls, 1)
        self.assertEqual(shtrih.cash_receipt['tag1021'], 'Иванов Иван')
        self.assertEqual(shtrih.cash_receipt['tag1203'], '123456789012')
        self.assertEqual(shtrih.tags_at_open, shtrih.cash_receipt)

    def test_does_not_reopen_active_shift(self):
        shtrih = FakeShtrih([2])
        self.assertEqual(open_shift(shtrih), 0)
        self.assertEqual(shtrih.open_calls, 0)

    def test_returns_error_for_connection_or_invalid_mode(self):
        self.assertNotEqual(open_shift(FakeShtrih([], connect_error=5)), 0)
        self.show_error.assert_called_with('Ошибка связи с кассой', 'Код 5: connection')
        self.show_error.reset_mock()
        self.assertNotEqual(open_shift(FakeShtrih([8])), 0)
        self.show_error.assert_called_with('Неверный режим кассы', 'Режим 8: mode')

    def test_returns_error_when_shift_does_not_open(self):
        with patch.object(operation_shtrih, 'get_cashier', return_value=('Иванов Иван', '123456789012', '1234567890')):
            self.assertNotEqual(open_shift(FakeShtrih([4, 4])), 0)

    def test_main_skips_print_setup_for_open_shift(self):
        shtrih = FakeShtrih([2])
        shtrih.print_on = lambda: self.fail('print_on must not run for open_shift')
        with patch.object(operation_shtrih, 'read_composition_receipt', return_value={'operationtype': 'open_shift'}), \
                patch.object(operation_shtrih, 'Shtrih', return_value=shtrih):
            self.assertEqual(operation_shtrih.main(), 0)

    def test_rsync_uses_exact_argv_and_ignores_failure(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(operation_shtrih.subprocess, 'run') as run, \
                patch.object(operation_shtrih.logger_operation_shtrih, 'warning') as warning:
            self.assertFalse(update_cashiers())
            run.assert_not_called()
            self.assertNotIn('user', str(warning.call_args))

        with patch.dict(os.environ, {'RSYNC_USER': 'user@', 'RSYNC_HOST': 'host'}, clear=False), \
                patch.object(operation_shtrih.subprocess, 'run', side_effect=OSError), \
                patch.object(operation_shtrih.logger_operation_shtrih, 'warning') as warning:
            self.assertFalse(update_cashiers())
            warning.assert_called_once()
            self.assertNotIn('user@host', str(warning.call_args))

        with patch.dict(os.environ, {'RSYNC_USER': 'user@', 'RSYNC_HOST': 'host'}, clear=False), \
                patch.object(operation_shtrih.subprocess, 'run') as run:
            run.return_value.returncode = 23
            self.assertFalse(update_cashiers())

        with patch.dict(os.environ, {'RSYNC_USER': 'user@', 'RSYNC_HOST': 'host'}, clear=False), \
                patch.object(operation_shtrih.subprocess, 'run') as run:
            run.return_value.returncode = 0
            self.assertTrue(update_cashiers())
            run.assert_called_once_with([
                r'D:\Rsync\bin\rsync.exe', '-rct', '--progress',
                'rsync://user@host/magazin/sotrud.txt',
                '/cygdrive/d/discont/sotrud.txt',
            ], shell=False, timeout=60)

    def test_find_cashier_requires_unique_valid_row(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sotrud.txt'
            path.write_text('7, Иванов Иван ,123456789012,1234567890\n', encoding='cp1251')
            self.assertEqual(find_cashier('7', path), ('Иванов Иван', '123456789012', '1234567890'))

            path.write_text('7,А,123456789012,1234567890\n7,Б,123456789012,1234567890\n', encoding='cp1251')
            with self.assertRaises(ValueError):
                find_cashier('7', path)

            for content in (
                    '8,Иванов Иван,123456789012,1234567890\n',
                    '7,Иванов Иван,123456789012\n',
                    '7,Иванов Иван,123,1234567890\n',
                    '7,Иванов Иван,123456789012,\n'):
                path.write_text(content, encoding='cp1251')
                with self.subTest(content=content), self.assertRaises(ValueError):
                    find_cashier('7', path)

            path.write_bytes(b'7,\x98,123456789012,1234567890\n')
            with self.assertRaises(UnicodeDecodeError):
                find_cashier('7', path)

        with self.assertRaises(FileNotFoundError):
            find_cashier('7', Path(directory) / 'missing.txt')

    def test_empty_inn_or_kkt_mismatch_blocks_shift(self):
        for cashier in (
                ('Иванов Иван', '', '1234567890'),
                ('Иванов Иван', '123456789012', ''),
                ('Иванов Иван', '123456789012', '9999999999')):
            shtrih = FakeShtrih([4], inn='1234567890')
            with self.subTest(cashier=cashier), patch.object(operation_shtrih, 'get_cashier', return_value=cashier):
                self.assertNotEqual(open_shift(shtrih), 0)
                self.assertEqual(shtrih.open_calls, 0)

        shtrih = FakeShtrih([4], inn='')
        with patch.object(operation_shtrih, 'get_cashier', return_value=('Иванов Иван', '123456789012', '1234567890')):
            self.assertNotEqual(open_shift(shtrih), 0)

    def test_fiscalization_error_blocks_shift_without_sensitive_log(self):
        shtrih = FakeShtrih([4])

        def fail_fiscalization():
            shtrih.drv.ResultCode = 9
            shtrih.drv.ResultCodeDescription = 'driver error'

        shtrih.drv.FNGetFiscalizationResult = fail_fiscalization
        with patch.object(operation_shtrih, 'get_cashier',
                          return_value=('Секретное ФИО', '123456789012', '1234567890')), \
                patch.object(operation_shtrih.logger_operation_shtrih, 'error') as error:
            self.assertNotEqual(open_shift(shtrih), 0)
            log_call = str(error.call_args)
            self.assertNotIn('Секретное ФИО', log_call)
            self.assertNotIn('123456789012', log_call)
            self.assertNotIn('1234567890', log_call)


if __name__ == '__main__':
    unittest.main()
