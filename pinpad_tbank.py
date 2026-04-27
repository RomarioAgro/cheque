from __future__ import annotations

import argparse
import configparser
import logging
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Optional, Union

import pythoncom
import win32com.client
import win32com.client.dynamic

from logger_config import get_logger
import getpass
import re


DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_CURRENCY_CODE = "643"
DEFAULT_INI_SECTION = "kassir1"

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


class DualConnectorError(Exception):
    pass


class DualConnectorResponseError(DualConnectorError):
    pass


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
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")

        self.error = 0
        self.text: Optional[str] = None
        self.last_result: Optional[OperationResult] = None

        self._com_initialized = False
        self._resources_initialized = False
        self._dc = None

        self.logger.debug(
            "init tid=%s ini_section=%s encoding=%s",
            self.tid,
            self.ini_section,
            self.encoding,
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
        return self._financial_operation(OperationCode.REFUND, amount, timeout_seconds)

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

    def _financial_operation(
        self,
        operation_code: int,
        amount: Union[int, float, str, Decimal],
        timeout_seconds: int,
    ) -> OperationResult:
        request = self._create_packet()
        request.Amount = self._amount_to_minor_units(amount)
        request.CurrencyCode = DEFAULT_CURRENCY_CODE
        request.OperationCode = operation_code
        request.TerminalID = self.tid
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

    def _exchange(self, request, timeout_seconds: int) -> OperationResult:
        self.logger.debug("create response packet start")
        response = self._create_packet()
        self.logger.debug("create response packet finish")
        self._log_packet_snapshot(response, "response initial")

        self.logger.debug("create/get dclink start")
        dc = self._get_or_create_dclink()
        self.logger.debug("create/get dclink finish")

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

        exchange_result = dc.Exchange(request, response, timeout_ms)
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
        choices=["payment", "refund", "reconcile_totals", "short_report", "full_report"],
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
    return parser


def main() -> None:
    logger = get_logger(__name__)
    parser = _build_arg_parser()
    args = parser.parse_args()
    # refund - -amount 1.00
    # sale - -amount 1.00
    client = TbankDC1(ini_section=args.section, logger=logger.getChild("TbankDC1"))
    operation_map = {
        "payment": lambda: client.payment(args.amount, timeout_seconds=args.timeout),
        "refund": lambda: client.refund(args.amount, timeout_seconds=args.timeout),
        "reconcile_totals": lambda: client.reconcile_totals(timeout_seconds=args.timeout),
        "short_report": lambda: client.short_report(timeout_seconds=args.timeout),
        "full_report": lambda: client.full_report(timeout_seconds=args.timeout),
    }

    if args.operation in {"payment", "refund"} and args.amount <= 0:
        parser.error("--amount must be greater than 0 for payment/refund")

    try:
        result = operation_map[args.operation]()
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
