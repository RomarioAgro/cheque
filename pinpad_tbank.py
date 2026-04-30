from __future__ import annotations

import argparse
import configparser
import logging
import sys
import socket
import tkinter as tk
from tkinter import simpledialog
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple, Union
import xml.etree.ElementTree as ET

import pythoncom
import win32com.client
import win32com.client.dynamic

from logger_config import get_logger
import getpass
import re


DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_CURRENCY_CODE = "643"
DEFAULT_INI_SECTION = "kassir1"
DEFAULT_POSGUI_ADDR = "127.0.0.1:6000"
DEFAULT_POSGUI_CODEPAGE = "windows-1251"
DEFAULT_POSGUI_CONNECT_TIMEOUT_SECONDS = 1.0
DEFAULT_POSGUI_RESPONSE_TIMEOUT_PADDING_SECONDS = 5.0
DEFAULT_POSGUI_MANUAL_DIALOGS = True
DEFAULT_POSGUI_OPERATION_DIALOG_TIMEOUT_SECONDS = 30
DEFAULT_POSGUI_RESULT_DIALOG_TIMEOUT_SECONDS = 3

def clean_garbage(text: str) -> str:
    """
    удаляем мусор из строки ответа тбанка
    :param text: str кусок ответа тбанка
    :return: str очищенный ответ от тбанка
    """
    patterns = [
        r'~?0xD[EF]\^\^[^~\n]*~?0xDD\^\^/~?',  # полный блок
        r'^\s*~?0xD[EF]\^\^\s*',  # только префикс в начале строки
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)
    return text.rstrip()

class OperationCode:
    SALE = 1
    REFUND = 4
    RECONCILE_TOTALS = 59
    USER_COMMAND = 63


class UserCommandCode:
    SHORT_REPORT = 20
    FULL_REPORT = 21


class PosGuiDialogType:
    INFO = 1
    CONFIRM = 2
    CHOICE = 3
    INPUT = 4
    PRINT = 5


class PosGuiMessageLevel:
    INFO = 1
    QUESTION = 2
    WARNING = 3
    ERROR = 4


class PosGuiButton:
    OK = 0x01
    YES = 0x02
    CANCEL = 0x04
    NO = 0x08


class PosGuiAnswer:
    NOTHING = 0
    OK = 1
    YES = 2
    CANCEL = 4
    NO = 8
    TIMEOUT = 16
    ESCAPE = 32
    INVALID_PARAMS = 64


class DualConnectorError(Exception):
    pass


class DualConnectorResponseError(DualConnectorError):
    pass


class PosGuiError(DualConnectorError):
    pass


class UserCancelledOperationError(DualConnectorError):
    def __init__(self, message: str = "Операция отменена пользователем", code: int = 2000) -> None:
        super().__init__(message)
        self.code = int(code)
        self.message = message


class RefundRrnDialog(simpledialog.Dialog):
    def __init__(self, parent, title: str) -> None:
        self.result_value: Optional[str] = None
        super().__init__(parent, title)

    def body(self, master):
        self.geometry("640x220")
        self.title_font = ("Arial", 20, "bold")
        self.entry_font = ("Arial", 20, "bold")
        tk.Label(
            master,
            text="Введите номер ссылки rrn",
            font=self.title_font,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(18, 10))
        self.entry = tk.Entry(master, width=40, font=self.entry_font)
        self.entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16)
        master.grid_columnconfigure(0, weight=1)
        master.grid_columnconfigure(1, weight=1)
        return self.entry

    def buttonbox(self):
        box = tk.Frame(self)
        button_font = ("Arial", 20, "bold")
        ok_btn = tk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE, font=button_font)
        ok_btn.pack(side=tk.LEFT, padx=10, pady=16)
        cancel_btn = tk.Button(box, text="Cancel", width=10, command=self.cancel, font=button_font)
        cancel_btn.pack(side=tk.LEFT, padx=10, pady=16)
        box.pack()
        self.bind("<Return>", lambda event: self.ok())
        self.bind("<Escape>", lambda event: self.cancel())

    def apply(self) -> None:
        self.result_value = self.entry.get()

    def cancel(self, event=None) -> None:
        super().cancel(event)


@dataclass
class OperationResult:
    exchange_result: int
    fields: Dict[str, str]
    session_id: str
    raw_response: Dict[str, str]

    @property
    def response_code_host(self) -> Optional[str]:
        return self.fields.get("15") or self.raw_response.get("ResponseCodeHost")

    @property
    def authorization_code(self) -> Optional[str]:
        return self.fields.get("13") or self.raw_response.get("AuthorizationCode")

    @property
    def reference_number(self) -> Optional[str]:
        return self.fields.get("14") or self.raw_response.get("ReferenceNumber")

    @property
    def text_response(self) -> Optional[str]:
        return self.fields.get("19") or self.raw_response.get("TextResponse")

    @property
    def receipt(self) -> Optional[str]:
        receipt = self.fields.get("90") or self.raw_response.get("ReceiptData")
        if receipt:
            return clean_garbage(receipt)
        return receipt

    @property
    def status(self) -> Optional[str]:
        return self.fields.get("39") or self.raw_response.get("Status")


@dataclass
class PosGuiResponse:
    dialog_type: int
    data: str
    adata: Optional[str]
    raw_response: str

    @property
    def answer_code(self) -> int:
        try:
            return int((self.data or "0").strip())
        except ValueError:
            return PosGuiAnswer.INVALID_PARAMS

    @property
    def selected_index(self) -> Optional[int]:
        if not self.adata:
            return None
        try:
            answer_mask = int(self.adata.strip())
        except ValueError:
            return None
        if answer_mask <= 0 or answer_mask & (answer_mask - 1):
            return None
        return answer_mask.bit_length() - 1


class PosGuiClient:
    def __init__(
        self,
        address: str = DEFAULT_POSGUI_ADDR,
        codepage: str = DEFAULT_POSGUI_CODEPAGE,
        connect_timeout_seconds: float = DEFAULT_POSGUI_CONNECT_TIMEOUT_SECONDS,
        response_timeout_padding_seconds: float = DEFAULT_POSGUI_RESPONSE_TIMEOUT_PADDING_SECONDS,
    ) -> None:
        self.address = address
        self.host, self.port = _parse_host_port(address)
        self.codepage = _normalize_codepage(codepage)
        self.connect_timeout_seconds = float(connect_timeout_seconds)
        self.response_timeout_padding_seconds = float(response_timeout_padding_seconds)

    def check_available(self) -> bool:
        try:
            with socket.create_connection(
                (self.host, self.port),
                timeout=self.connect_timeout_seconds,
            ):
                return True
        except OSError as exc:
            raise PosGuiError(f"DC PosGUI is unavailable at {self.address}: {exc}") from exc

    def show_info(
        self,
        title: str,
        message: str,
        timeout_seconds: int = 10,
        level: int = PosGuiMessageLevel.INFO,
    ) -> PosGuiResponse:
        data = self._display_data(level, None, title, message)
        return self.send_request(PosGuiDialogType.INFO, data, timeout_seconds=timeout_seconds)

    def show_confirm(
        self,
        title: str,
        message: str,
        timeout_seconds: int = 30,
        buttons: int = PosGuiButton.OK | PosGuiButton.CANCEL,
        level: int = PosGuiMessageLevel.QUESTION,
    ) -> PosGuiResponse:
        data = self._display_data(level, buttons, title, message)
        return self.send_request(PosGuiDialogType.CONFIRM, data, timeout_seconds=timeout_seconds)

    def show_choice(
        self,
        title: str,
        message: str,
        choices: Iterable[str],
        timeout_seconds: int = 30,
        buttons: int = PosGuiButton.OK,
        level: int = PosGuiMessageLevel.QUESTION,
    ) -> PosGuiResponse:
        choice_items = [self._sanitize_field(choice) for choice in choices]
        if not choice_items:
            raise ValueError("choices must contain at least one item")
        data = self._display_data(level, buttons, title, message)
        adata = "\n".join(choice_items)
        return self.send_request(
            PosGuiDialogType.CHOICE,
            data,
            adata=adata,
            timeout_seconds=timeout_seconds,
        )

    def show_input(
        self,
        title: str,
        message: str,
        mask: str = "",
        timeout_seconds: int = 30,
        buttons: int = PosGuiButton.OK,
        level: int = PosGuiMessageLevel.QUESTION,
    ) -> PosGuiResponse:
        data = self._display_data(level, buttons, title, message)
        return self.send_request(
            PosGuiDialogType.INPUT,
            data,
            adata=self._sanitize_field(mask),
            timeout_seconds=timeout_seconds,
        )

    def print_data(self, data: str) -> PosGuiResponse:
        return self.send_request(PosGuiDialogType.PRINT, self._sanitize_field(data))

    def send_request(
        self,
        dialog_type: int,
        data: str,
        adata: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        response_timeout_seconds: Optional[float] = None,
    ) -> PosGuiResponse:
        request_bytes = self._build_request_xml(
            dialog_type=dialog_type,
            data=data,
            adata=adata,
            timeout_seconds=timeout_seconds,
        )
        socket_timeout = self._socket_timeout(timeout_seconds, response_timeout_seconds)
        try:
            with socket.create_connection(
                (self.host, self.port),
                timeout=self.connect_timeout_seconds,
            ) as sock:
                sock.settimeout(socket_timeout)
                sock.sendall(request_bytes)
                try:
                    sock.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                response = self._read_response(sock)
        except OSError as exc:
            raise PosGuiError(f"DC PosGUI request failed at {self.address}: {exc}") from exc

        if response.dialog_type != int(dialog_type):
            raise PosGuiError(
                f"Unexpected DC PosGUI response type: {response.dialog_type}, expected {dialog_type}"
            )
        return response

    def _build_request_xml(
        self,
        dialog_type: int,
        data: str,
        adata: Optional[str],
        timeout_seconds: Optional[int],
    ) -> bytes:
        root = ET.Element("request")
        ET.SubElement(root, "type").text = str(int(dialog_type))
        ET.SubElement(root, "data").text = data
        if adata is not None:
            ET.SubElement(root, "adata").text = adata
        if timeout_seconds is not None:
            ET.SubElement(root, "timeout").text = str(int(timeout_seconds))
        return ET.tostring(root, encoding=self.codepage, method="xml")

    def _read_response(self, sock: socket.socket) -> PosGuiResponse:
        chunks = []
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout as exc:
                raise PosGuiError("DC PosGUI response timeout") from exc
            if not chunk:
                break
            chunks.append(chunk)
            if b"</response>" in b"".join(chunks).lower():
                break

        if not chunks:
            raise PosGuiError("DC PosGUI returned empty response")

        raw_response = b"".join(chunks).decode(self.codepage, errors="replace").strip()
        try:
            root = ET.fromstring(raw_response)
        except ET.ParseError as exc:
            raise PosGuiError(f"Invalid DC PosGUI response XML: {raw_response!r}") from exc

        if root.tag != "response":
            raise PosGuiError(f"Invalid DC PosGUI response root: {root.tag}")

        dialog_type_raw = root.findtext("type", default="0")
        try:
            dialog_type = int(dialog_type_raw.strip())
        except ValueError as exc:
            raise PosGuiError(f"Invalid DC PosGUI response type: {dialog_type_raw!r}") from exc

        return PosGuiResponse(
            dialog_type=dialog_type,
            data=root.findtext("data", default=""),
            adata=root.findtext("adata"),
            raw_response=raw_response,
        )

    def _socket_timeout(
        self,
        request_timeout_seconds: Optional[int],
        response_timeout_seconds: Optional[float],
    ) -> float:
        if response_timeout_seconds is not None:
            return float(response_timeout_seconds)
        if request_timeout_seconds is None:
            return self.connect_timeout_seconds + self.response_timeout_padding_seconds
        return float(request_timeout_seconds) + self.response_timeout_padding_seconds

    @staticmethod
    def _display_data(
        level: Optional[int],
        buttons: Optional[int],
        title: str,
        message: str,
    ) -> str:
        level_text = "" if level is None else str(int(level))
        buttons_text = "" if buttons is None else str(int(buttons))
        return "^".join(
            (
                level_text,
                buttons_text,
                PosGuiClient._sanitize_field(title),
                PosGuiClient._sanitize_field(message),
            )
        )

    @staticmethod
    def _sanitize_field(value: object) -> str:
        return str(value).replace("^", " ").replace("\r\n", "\n").replace("\r", "\n")


def _normalize_codepage(codepage: str) -> str:
    value = str(codepage or DEFAULT_POSGUI_CODEPAGE).strip()
    if value.isdigit():
        return f"cp{value}"
    return value


def _parse_host_port(address: str, default_port: int = 6000) -> Tuple[str, int]:
    value = str(address or "").strip()
    if not value:
        raise ValueError("address is empty")
    if "://" in value:
        from urllib.parse import urlparse

        parsed = urlparse(value)
        if not parsed.hostname:
            raise ValueError(f"Invalid address: {address}")
        return parsed.hostname, parsed.port or default_port

    host, separator, port = value.rpartition(":")
    if separator and host and port.isdigit():
        return host.strip("[]"), int(port)
    return value.strip("[]"), default_port


def _parse_bool(value: Optional[object], default: bool = False) -> bool:
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on", "y", "да"}:
        return True
    if normalized in {"0", "false", "no", "off", "n", "нет"}:
        return False
    return default


def _load_ini_section(section_name: str = DEFAULT_INI_SECTION) -> Dict[str, str]:
    config_path = Path(__file__).with_name("tbank.ini")
    config = configparser.ConfigParser()
    if not config_path.exists():
        return {}
    config.read(config_path, encoding="utf-8")
    if not config.has_section(section_name):
        return {}
    return dict(config[section_name])

def get_cashier():
    """
    получаем имя юзера, по этому имени
    в ini файле есть секция с параметрами
    :return:
    """
    cashier = getpass.getuser().lower()
    if 'kassir' in cashier:
        return cashier
    else:
        return 'kassir1'

class TbankDC1:
    def __init__(
        self,
        base_url: Optional[str] = None,
        tid: Optional[str] = None,
        ini_section: str = get_cashier(),
        encoding: str = "windows-1251",
        posgui_addr: Optional[str] = None,
        posgui_enabled: Optional[bool] = None,
        posgui_required: Optional[bool] = None,
        posgui_codepage: Optional[str] = None,
        posgui_manual_dialogs: Optional[bool] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:

        ini_config = _load_ini_section(ini_section)
        resolved_tid = (tid or ini_config.get("tid", "")).strip()

        if not resolved_tid:
            raise ValueError(f"Terminal ID is not configured in tbank.ini section [{ini_section}]")

        self.base_url = (base_url or ini_config.get("url", "")).strip()
        self.tid = resolved_tid
        self.ini_section = ini_section
        self.encoding = encoding
        self.posgui_addr = (
            posgui_addr
            or ini_config.get("posgui_addr")
            or ini_config.get("gui_addr")
            or DEFAULT_POSGUI_ADDR
        ).strip()
        self.posgui_enabled = (
            _parse_bool(posgui_enabled, True)
            if posgui_enabled is not None
            else _parse_bool(ini_config.get("posgui_enabled"), True)
        )
        self.posgui_required = (
            _parse_bool(posgui_required, False)
            if posgui_required is not None
            else _parse_bool(ini_config.get("posgui_required"), False)
        )
        self.posgui_codepage = (
            posgui_codepage
            or ini_config.get("posgui_codepage")
            or DEFAULT_POSGUI_CODEPAGE
        ).strip()
        self.posgui_manual_dialogs = (
            _parse_bool(posgui_manual_dialogs, DEFAULT_POSGUI_MANUAL_DIALOGS)
            if posgui_manual_dialogs is not None
            else _parse_bool(ini_config.get("posgui_manual_dialogs"), DEFAULT_POSGUI_MANUAL_DIALOGS)
        )
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")

        self.error = 0
        self.text: Optional[str] = None
        self.last_result: Optional[OperationResult] = None

        self._com_initialized = False
        self._resources_initialized = False
        self._dc = None
        self._posgui_checked = False
        self._posgui_client = (
            PosGuiClient(self.posgui_addr, codepage=self.posgui_codepage)
            if self.posgui_enabled
            else None
        )

        self.logger.debug(
            "init tid=%s ini_section=%s encoding=%s posgui_enabled=%s posgui_addr=%s posgui_manual_dialogs=%s",
            self.tid,
            self.ini_section,
            self.encoding,
            self.posgui_enabled,
            self.posgui_addr,
            self.posgui_manual_dialogs,
        )

    def _log_packet_snapshot(self, packet, title: str) -> None:
        interesting_properties = (
            "Amount",
            "CurrencyCode",
            "OperationCode",
            "TerminalID",
            "CommandMode",
            "Status",
            "ResponseCodeHost",
            "TextResponse",
            "ReferenceNumber",
            "AuthorizationCode",
            "ReceiptData",
        )
        snapshot: Dict[str, str] = {}
        for property_name in interesting_properties:
            try:
                value = getattr(packet, property_name)
            except Exception as exc:
                snapshot[property_name] = f"<error: {exc}>"
                continue
            if value not in (None, "", -1):
                snapshot[property_name] = str(value)
        self.logger.debug("%s %s", title, snapshot)

    def pinpad_operation(self,
                  operation_name: str = "x_otchet",
                  amount: Union[int, float, str, Decimal] = 0
                  ):
        operation = (operation_name or "").strip().lower()

        if operation in ("sale", "payment", "oplata", "1"):
            return self.payment(amount)
        if operation in ("return_sale", "refund", "vozvrat", "4"):
            return self.refund(amount)
        if operation in ("x_otchet", "short_report", "kratkiy_otchet"):
            return self.short_report()
        if operation in ("full_otchet", "full_report", "polniy_otchet"):
            return self.full_report()
        if operation in ("z_otchet", "reconciliation", "reconcile_totals", "sverka_itogov"):
            return self.reconcile_totals()

        raise ValueError(f"Unsupported pinpad operation: {operation_name}")

    def payment(
        self,
        amount: Union[int, float, str, Decimal],
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> OperationResult:
        return self._financial_operation(OperationCode.SALE, amount, timeout_seconds)

    def refund(
        self,
        amount: Union[int, float, str, Decimal],
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> OperationResult:
        rrn = self._request_refund_rrn()
        return self._financial_operation(
            OperationCode.REFUND,
            amount,
            timeout_seconds,
            reference_number=rrn,
        )

    def reconcile_totals(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> OperationResult:
        request = self._create_packet()
        request.CurrencyCode = DEFAULT_CURRENCY_CODE
        request.OperationCode = OperationCode.RECONCILE_TOTALS
        request.TerminalID = self.tid
        return self._exchange(request, timeout_seconds)

    def short_report(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> OperationResult:
        return self._user_command(UserCommandCode.SHORT_REPORT, timeout_seconds)

    def full_report(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> OperationResult:
        return self._user_command(UserCommandCode.FULL_REPORT, timeout_seconds)

    def oplata(
        self,
        amount: Union[int, float, str, Decimal],
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> OperationResult:
        return self.payment(amount, timeout_seconds)

    def vozvrat(
        self,
        amount: Union[int, float, str, Decimal],
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> OperationResult:
        return self.refund(amount, timeout_seconds)

    def sverka_itogov(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> OperationResult:
        return self.reconcile_totals(timeout_seconds)

    def kratkiy_otchet(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> OperationResult:
        return self.short_report(timeout_seconds)

    def polniy_otchet(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> OperationResult:
        return self.full_report(timeout_seconds)

    def close(self) -> None:
        if self._dc is not None and self._resources_initialized:
            try:
                self.logger.debug("FreeResources start")
                _ = self._dc.FreeResources
                self.logger.debug("FreeResources finish")
            finally:
                self._resources_initialized = False

        self._dc = None
        if self._com_initialized:
            self.logger.debug("CoUninitialize start")
            pythoncom.CoUninitialize()
            self._com_initialized = False
            self.logger.debug("CoUninitialize finish")

    def close_open_connection(self) -> None:
        raise NotImplementedError("close_open_connection is not used in COM mode")

    def get_receipt_bytes(self, result: Optional[OperationResult] = None) -> bytes:
        operation_result = result or self.last_result
        if operation_result is None:
            return b""
        receipt = operation_result.receipt or ""
        return receipt.encode(self.encoding, errors="replace")

    def posgui_show_info(
        self,
        title: str,
        message: str,
        timeout_seconds: int = 10,
        level: int = PosGuiMessageLevel.INFO,
    ) -> PosGuiResponse:
        return self._get_posgui_client().show_info(title, message, timeout_seconds, level)

    def posgui_show_confirm(
        self,
        title: str,
        message: str,
        timeout_seconds: int = 30,
        buttons: int = PosGuiButton.OK | PosGuiButton.CANCEL,
        level: int = PosGuiMessageLevel.QUESTION,
    ) -> PosGuiResponse:
        return self._get_posgui_client().show_confirm(title, message, timeout_seconds, buttons, level)

    def posgui_show_choice(
        self,
        title: str,
        message: str,
        choices: Iterable[str],
        timeout_seconds: int = 30,
        buttons: int = PosGuiButton.OK,
        level: int = PosGuiMessageLevel.QUESTION,
    ) -> PosGuiResponse:
        return self._get_posgui_client().show_choice(
            title,
            message,
            choices,
            timeout_seconds,
            buttons,
            level,
        )

    def posgui_show_input(
        self,
        title: str,
        message: str,
        mask: str = "",
        timeout_seconds: int = 30,
        buttons: int = PosGuiButton.OK,
        level: int = PosGuiMessageLevel.QUESTION,
    ) -> PosGuiResponse:
        return self._get_posgui_client().show_input(
            title,
            message,
            mask,
            timeout_seconds,
            buttons,
            level,
        )

    def _financial_operation(
        self,
        operation_code: int,
        amount: Union[int, float, str, Decimal],
        timeout_seconds: int,
        reference_number: Optional[str] = None,
    ) -> OperationResult:
        request = self._create_packet()
        request.Amount = self._amount_to_minor_units(amount)
        request.CurrencyCode = DEFAULT_CURRENCY_CODE
        request.OperationCode = operation_code
        request.TerminalID = self.tid
        if reference_number:
            request.ReferenceNumber = reference_number
        self._log_packet_snapshot(request, "request prepared")
        return self._exchange(request, timeout_seconds)

    def _user_command(self, command_code: int, timeout_seconds: int) -> OperationResult:
        request = self._create_packet()
        request.CurrencyCode = DEFAULT_CURRENCY_CODE
        request.OperationCode = OperationCode.USER_COMMAND
        request.TerminalID = self.tid
        # User command code must be sent in field 65. CommandMode serializes to field 64,
        # which does not trigger report operations on this terminal profile.
        request.SetFieldInt(65, int(command_code))
        self._log_packet_snapshot(request, "request prepared")
        return self._exchange(request, timeout_seconds)

    def _request_refund_rrn(self) -> Optional[str]:
        title = "Введите номер ссылки rrn"
        self.logger.debug("refund rrn dialog shown title=%r", title)
        root = tk.Tk()
        root.withdraw()
        try:
            dialog = RefundRrnDialog(root, title)
            rrn = dialog.result_value
        finally:
            root.destroy()

        self.logger.debug("refund rrn dialog response rrn=%r", rrn)

        if rrn is None:
            self.logger.warning("refund rrn dialog cancelled")
            raise UserCancelledOperationError()

        rrn = rrn.strip()
        if rrn:
            self.logger.debug("refund rrn prompt accepted rrn=%r", rrn)
            return rrn

        self.logger.debug("refund rrn prompt accepted with empty rrn")
        return None

    def _exchange(self, request, timeout_seconds: int) -> OperationResult:
        self.logger.debug("create response packet start")
        response = self._create_packet()
        self.logger.debug("create response packet finish")
        self._log_packet_snapshot(response, "response initial")

        self.logger.debug("create/get dclink start")
        dc = self._get_or_create_dclink()
        self.logger.debug("create/get dclink finish")

        self._ensure_posgui_available()

        self.logger.debug("InitResources ensure start")
        self._ensure_resources(dc)
        self.logger.debug("InitResources ensure finish")
        timeout_ms = int(timeout_seconds * 1000)

        self.logger.debug(
            "exchange start operation=%s terminal_id=%s amount=%s command=%s timeout_seconds=%s timeout_ms=%s",
            getattr(request, "OperationCode", None),
            getattr(request, "TerminalID", None),
            getattr(request, "Amount", None),
            getattr(request, "CommandMode", None),
            timeout_seconds,
            timeout_ms,
        )

        self._show_operation_start_dialog(request)
        try:
            exchange_result = dc.Exchange(request, response, timeout_ms)
        except Exception:
            self._show_posgui_info_safe(
                "T-Bank",
                "Ошибка обмена с терминалом",
                timeout_seconds=DEFAULT_POSGUI_RESULT_DIALOG_TIMEOUT_SECONDS,
                level=PosGuiMessageLevel.ERROR,
            )
            raise
        self.logger.debug(
            "exchange raw finish result=%s error_code=%s error_description=%s",
            exchange_result,
            getattr(dc, "ErrorCode", None),
            getattr(dc, "ErrorDescription", None),
        )
        self._log_packet_snapshot(response, "response after exchange")
        fields = self._extract_fields(response)
        raw_response = self._extract_response_properties(response)
        self.logger.debug("response fields=%s", fields)
        self.logger.debug("response raw_properties=%s", raw_response)
        result = OperationResult(
            exchange_result=exchange_result,
            fields=fields,
            session_id="",
            raw_response=raw_response,
        )

        self.last_result = result
        self.text = result.receipt or result.text_response or ""
        self.error = self._resolve_error_code(result)
        self._show_operation_result_dialog(result)

        self.logger.debug(
            "exchange finish exchange_result=%s status=%s host_code=%s text=%s",
            exchange_result,
            result.status,
            result.response_code_host,
            result.text_response,
        )

        if exchange_result != 0:
            raise DualConnectorResponseError(
                f"Exchange failed: {exchange_result}, status={result.status}, text={result.text_response or ''}"
            )

        return result

    def _get_posgui_client(self) -> PosGuiClient:
        if self._posgui_client is None:
            raise PosGuiError("DC PosGUI support is disabled")
        return self._posgui_client

    def _ensure_posgui_available(self) -> None:
        if not self.posgui_enabled or self._posgui_checked:
            return
        try:
            self._get_posgui_client().check_available()
        except PosGuiError:
            self._posgui_checked = True
            if self.posgui_required:
                raise
            self.logger.warning("DC PosGUI is not available at %s", self.posgui_addr, exc_info=True)
            return
        self._posgui_checked = True
        self.logger.debug("DC PosGUI is available at %s", self.posgui_addr)

    def _show_operation_start_dialog(self, request) -> None:
        if not self.posgui_manual_dialogs:
            return
        operation_code = self._safe_int(getattr(request, "OperationCode", None))
        title = self._operation_title(operation_code)
        message = self._operation_start_message(operation_code, getattr(request, "Amount", None))
        self._show_posgui_info_safe(
            title,
            message,
            timeout_seconds=DEFAULT_POSGUI_OPERATION_DIALOG_TIMEOUT_SECONDS,
            level=PosGuiMessageLevel.INFO,
        )

    def _show_operation_result_dialog(self, result: OperationResult) -> None:
        if not self.posgui_manual_dialogs:
            return
        if result.exchange_result == 0 and (result.status or "").strip() == "1":
            message = result.text_response or "Операция выполнена"
            level = PosGuiMessageLevel.INFO
        else:
            message = result.text_response or "Операция не выполнена"
            level = PosGuiMessageLevel.WARNING
        self._show_posgui_info_safe(
            "T-Bank",
            message,
            timeout_seconds=DEFAULT_POSGUI_RESULT_DIALOG_TIMEOUT_SECONDS,
            level=level,
        )

    def _show_posgui_info_safe(
        self,
        title: str,
        message: str,
        timeout_seconds: int,
        level: int,
    ) -> None:
        if not self.posgui_enabled:
            return
        try:
            self._get_posgui_client().show_info(
                title,
                message,
                timeout_seconds=timeout_seconds,
                level=level,
            )
        except PosGuiError:
            if self.posgui_required:
                raise
            self.logger.warning("DC PosGUI dialog was not shown", exc_info=True)

    @staticmethod
    def _operation_title(operation_code: Optional[int]) -> str:
        if operation_code == OperationCode.SALE:
            return "T-Bank: оплата"
        if operation_code == OperationCode.REFUND:
            return "T-Bank: возврат"
        if operation_code == OperationCode.RECONCILE_TOTALS:
            return "T-Bank: сверка итогов"
        if operation_code == OperationCode.USER_COMMAND:
            return "T-Bank: отчет"
        return "T-Bank"

    def _operation_start_message(
        self,
        operation_code: Optional[int],
        amount: Optional[object],
    ) -> str:
        amount_text = self._format_minor_units(amount)
        if operation_code == OperationCode.SALE:
            return f"Приложите карту к терминалу\nСумма: {amount_text} РУБ"
        if operation_code == OperationCode.REFUND:
            return f"Приложите карту к терминалу\nСумма возврата: {amount_text} РУБ"
        if operation_code == OperationCode.RECONCILE_TOTALS:
            return "Выполняется сверка итогов"
        if operation_code == OperationCode.USER_COMMAND:
            return "Формируется отчет терминала"
        return "Выполняется операция на терминале"

    @staticmethod
    def _format_minor_units(amount: Optional[object]) -> str:
        try:
            value = Decimal(str(amount or "0")) / Decimal("100")
        except Exception:
            return str(amount or "0")
        return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"

    @staticmethod
    def _safe_int(value: Optional[object]) -> Optional[int]:
        try:
            return int(value)
        except Exception:
            return None

    def _get_or_create_dclink(self):
        if not self._com_initialized:
            self.logger.debug("CoInitialize start")
            pythoncom.CoInitialize()
            self._com_initialized = True
            self.logger.debug("CoInitialize finish")

        if self._dc is None:
            self.logger.debug("DCLink create start")
            self._dc = win32com.client.dynamic.Dispatch("DualConnector.DCLink")
            self.logger.debug("DCLink create finish type=%s", type(self._dc))

        return self._dc

    def _ensure_resources(self, dc) -> None:
        if not self._resources_initialized:
            init_result = dc.InitResources
            self.logger.debug(
                "InitResources result=%s error_code=%s error_description=%s",
                init_result,
                getattr(dc, "ErrorCode", None),
                getattr(dc, "ErrorDescription", None),
            )
            if init_result != 0:
                error_text = getattr(dc, "ErrorDescription", "")
                raise DualConnectorError(f"InitResources failed: {init_result} - {error_text}")
            self._resources_initialized = True

    @staticmethod
    def _create_packet():
        return win32com.client.dynamic.Dispatch("DualConnector.SAPacket")

    @staticmethod
    def _extract_fields(packet) -> Dict[str, str]:
        fields: Dict[str, str] = {}
        for field_id in ("13", "14", "15", "19", "39", "90"):
            try:
                value = packet.GetField(int(field_id))
            except Exception:
                value = None
            if value not in (None, ""):
                fields[field_id] = str(value)
        return fields

    @staticmethod
    def _extract_response_properties(packet) -> Dict[str, str]:
        property_names = (
            "AuthorizationCode",
            "ReferenceNumber",
            "ResponseCodeHost",
            "TextResponse",
            "ReceiptData",
            "Status",
            "TerminalID",
            "OperationCode",
            "CommandMode",
            "SlipNumber",
            "TerminalTrxID",
            "HostTrxID",
            "Acquirer",
        )
        result: Dict[str, str] = {}
        for property_name in property_names:
            try:
                value = getattr(packet, property_name)
            except Exception:
                continue
            if value not in (None, ""):
                result[property_name] = str(value)
        return result

    @staticmethod
    def _amount_to_minor_units(amount: Union[int, float, str, Decimal]) -> str:
        decimal_amount = Decimal(str(amount))
        if decimal_amount < 0:
            raise ValueError(f"Invalid amount: {amount}")
        return str((decimal_amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _resolve_error_code(result: OperationResult) -> int:
        if result.exchange_result != 0:
            return int(result.exchange_result)
        host_code = result.response_code_host
        if host_code and host_code.lstrip("-").isdigit():
            return int(host_code)
        return 0

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


class Tbank(TbankDC1):
    pass


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manual test client for T-Bank Dual Connector DC1 COM mode")
    parser.add_argument(
        "operation",
        choices=[
            "payment",
            "refund",
            "reconcile_totals",
            "short_report",
            "full_report",
            "posgui_info",
        ],
        help="Terminal operation to execute",
    )
    parser.add_argument(
        "--amount",
        type=Decimal,
        default=Decimal("0"),
        help="Amount in rubles for payment/refund operations",
    )
    parser.add_argument(
        "--section",
        default=DEFAULT_INI_SECTION,
        help="INI section name in tbank.ini",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Operation timeout in seconds",
    )
    parser.add_argument(
        "--posgui-addr",
        default=None,
        help="DC PosGUI endpoint, for example 127.0.0.1:6000",
    )
    parser.add_argument(
        "--gui-title",
        default="T-Bank",
        help="Title for posgui_info",
    )
    parser.add_argument(
        "--gui-message",
        default="DC PosGUI test",
        help="Message for posgui_info",
    )
    parser.add_argument(
        "--gui-timeout",
        type=int,
        default=3,
        help="Dialog timeout in seconds for posgui_info",
    )
    return parser


def main() -> None:
    logger = get_logger(__name__)
    parser = _build_arg_parser()
    args = parser.parse_args()
    # refund - -amount 1.00
    # sale - -amount 1.00
    client = TbankDC1(
        ini_section=args.section,
        posgui_addr=args.posgui_addr,
        logger=logger.getChild("TbankDC1"),
    )
    operation_map = {
        "payment": lambda: client.payment(args.amount, timeout_seconds=args.timeout),
        "refund": lambda: client.refund(args.amount, timeout_seconds=args.timeout),
        "reconcile_totals": lambda: client.reconcile_totals(timeout_seconds=args.timeout),
        "short_report": lambda: client.short_report(timeout_seconds=args.timeout),
        "full_report": lambda: client.full_report(timeout_seconds=args.timeout),
    }

    if args.operation == "posgui_info":
        try:
            response = client.posgui_show_info(
                args.gui_title,
                args.gui_message,
                timeout_seconds=args.gui_timeout,
            )
        finally:
            client.close()
        print(f"posgui_type: {response.dialog_type}")
        print(f"posgui_answer: {response.answer_code}")
        print(f"posgui_raw: {response.raw_response}")
        return

    if args.operation in {"payment", "refund"} and args.amount <= 0:
        parser.error("--amount must be greater than 0 for payment/refund")

    try:
        result = operation_map[args.operation]()
    except UserCancelledOperationError as exc:
        print(f"error_code: {exc.code}")
        print(f"error: {exc.message}")
        sys.exit(1)
    finally:
        client.close()

    print(f"exchange_result: {result.exchange_result}")
    print(f"status: {result.status}")
    print(f"host_code: {result.response_code_host}")
    print(f"auth_code: {result.authorization_code}")
    print(f"rrn: {result.reference_number}")
    print(f"text: {result.text_response or ''}")
    print(f"receipt: {result.receipt or ''}")
    print("raw_response:")
    for key, value in result.raw_response.items():
        print(f"  {key}: {value}")

# refund --amount 1.00
if __name__ == "__main__":
    main()
