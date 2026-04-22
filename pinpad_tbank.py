from __future__ import annotations

import configparser
import time
import uuid
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Optional, Union
from xml.etree import ElementTree as ET

import requests


# ====== SETTINGS ======
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_CURRENCY_CODE = "643"  # RUB


def _load_tbank_ini() -> Dict[str, str]:
    config_path = Path(__file__).with_name("tbank.ini")
    config = configparser.ConfigParser()
    if not config_path.exists():
        return {}
    config.read(config_path, encoding="utf-8")
    if not config.has_section("tbank"):
        return {}
    return dict(config["tbank"])


_TBANK_INI_CONFIG = _load_tbank_ini()


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
    SALE = "1"
    REFUND = "4"
    RECONCILE_TOTALS = "59"
    USER_COMMAND = "63"


class UserCommandCode:
    SHORT_REPORT = "20"
    FULL_REPORT = "21"
    RECEIPT_COPY = "22"


class DualConnectorError(Exception):
    pass


class DualConnectorResponseError(DualConnectorError):
    pass


@dataclass
class OperationResult:
    raw_xml: str
    fields: Dict[str, str]
    session_id: str

    @property
    def response_code_host(self) -> Optional[str]:
        return self.fields.get("15")

    @property
    def authorization_code(self) -> Optional[str]:
        return self.fields.get("13")

    @property
    def reference_number(self) -> Optional[str]:
        return self.fields.get("14")

    @property
    def text_response(self) -> Optional[str]:
        return self.fields.get("19")

    @property
    def status(self) -> Optional[str]:
        return self.fields.get("39")


class Tbank:
    def __init__(
        self,
        base_url: Optional[str] = None,
        tid: Optional[str] = None,
        encoding: str = "windows-1251",
    ) -> None:
        resolved_base_url = base_url or _TBANK_INI_CONFIG.get("base_url")
        resolved_terminal_id = tid
        if resolved_terminal_id is None:
            resolved_terminal_id = _TBANK_INI_CONFIG.get("tid_kassir1")

        self.base_url = resolved_base_url.rstrip("/")
        self.tid = resolved_terminal_id
        self.encoding = encoding
        self.text = None

    # =========================
    # PUBLIC API
    # =========================
    def pinpad_operation(self, operation_name: str = 'x_otchet', amount: int = 0):
        """
        так сказать прокси для вызова методов
        :param operation_name:
        :param amount:
        :return:
        """
        if operation_name in ("sale", "1"):
            return self.operation("sale", amount)

        if operation_name in ("return_sale", "refund", "4"):
            return self.operation("refund", amount)

        if operation_name in ("short_report", "x_otchet"):
            return self.short_report()

        if operation_name in ("full_report", "full_otchet"):
            return self.full_report()

        if operation_name == "z_otchet":
            return self.reconcile_totals()

        raise ValueError(f"Unsupported pinpad operation: {operation_name}")


    def operation(
        self,
        operation_type: str,
        amount: Union[int, float, str, Decimal],
        # terminal_id: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    ) -> OperationResult:
        op = (operation_type or "").strip().lower()
        if op in ("sale", OperationCode.SALE):
            operation_code = OperationCode.SALE
        elif op in ("refund", "return_sale", OperationCode.REFUND):
            operation_code = OperationCode.REFUND
        else:
            raise ValueError(f"Unsupported operation_type: {operation_type}")

        amount_minor = self._amount_to_minor_units(amount)

        fields = {
            "00": amount_minor,
            "04": DEFAULT_CURRENCY_CODE,
            "21": self._now_terminal_datetime(),
            "25": operation_code,
            "27": self.tid,
        }
        return self._send_request(fields, timeout_seconds)

    def reconcile_totals(
        self,
        terminal_id: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> OperationResult:
        fields = {
            "04": DEFAULT_CURRENCY_CODE,
            "21": self._now_terminal_datetime(),
            "25": OperationCode.RECONCILE_TOTALS,
        }

        effective_terminal_id = terminal_id or self.tid
        if effective_terminal_id:
            fields["27"] = effective_terminal_id

        return self._send_request(fields, timeout_seconds)

    def user_command(
        self,
        command_code: str,
        terminal_id: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> OperationResult:
        """
        Operation 65: execute a user command.

        """
        fields = {
            "04": DEFAULT_CURRENCY_CODE,
            "21": self._now_terminal_datetime(),
            "25": OperationCode.USER_COMMAND,
            "65": str(command_code),
        }

        effective_terminal_id = terminal_id or self.tid
        if effective_terminal_id:
            fields["27"] = effective_terminal_id

        return self._send_request(fields, timeout_seconds)

    def short_report(
        self,
        terminal_id: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> OperationResult:
        return self.user_command(
            command_code=UserCommandCode.SHORT_REPORT,
            terminal_id=terminal_id,
            timeout_seconds=timeout_seconds,
        )

    def full_report(
        self,
        terminal_id: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> OperationResult:
        return self.user_command(
            command_code=UserCommandCode.FULL_REPORT,
            terminal_id=terminal_id,
            timeout_seconds=timeout_seconds,
        )

    def receipt_copy(
        self,
        receipt_number: str,
        receipt_date: Optional[str] = None,
        terminal_id: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> OperationResult:
        """
        Operation 63 / command 22 (receipt copy).
        Exact extra fields depend on host configuration.
        Safe baseline:
        - 80 = 22
        - 81 = receipt number
        - 06 or 21 may carry receipt date/time if required by host
        """
        fields = {
            "04": DEFAULT_CURRENCY_CODE,
            "21": self._now_terminal_datetime(),
            "25": OperationCode.USER_COMMAND,
            "80": UserCommandCode.RECEIPT_COPY,
            "81": receipt_number,
        }

        if receipt_date:
            fields["06"] = receipt_date  # YYYYMMDDHHMMSS if required by host

        effective_terminal_id = terminal_id or self.tid
        if effective_terminal_id:
            fields["27"] = effective_terminal_id

        return self._send_request(fields, timeout_seconds)

    def close_open_connection(self, terminal_id: str) -> requests.Response:
        url = f"{self.base_url}/command/closeOpenConnection"
        response = requests.post(
            url,
            params={"TerminalId": terminal_id},
            timeout=15,
        )
        response.raise_for_status()
        return response

    # =========================
    # INTERNALS
    # =========================

    def _send_request(self, fields: Dict[str, str], timeout_seconds: int) -> OperationResult:
        session_id = self._generate_session_id()
        xml_payload = self._build_request_xml(fields, timeout_seconds, session_id)

        headers = {
            "Content-Type": f"text/xml; charset={self.encoding}",
            "Accept": "text/xml",
            "Accept-Charset": self.encoding,
        }
        response = requests.post(
            self.base_url,
            data=xml_payload.encode(self.encoding),
            headers=headers,
            timeout=timeout_seconds + 10,
        )
        response.raise_for_status()

        raw_text = response.content.decode(self.encoding, errors="replace")
        parsed = self._parse_response_xml(raw_text)
        self.text = clean_garbage(parsed.get('90', ''))
        if "errorcode" in parsed:
            raise DualConnectorResponseError(
                f"DC Service error {parsed.get('errorcode')}: {parsed.get('errordescription', '')}"
            )

        return OperationResult(
            raw_xml=raw_text,
            fields=parsed,
            session_id=session_id,
        )

    def _build_request_xml(
        self,
        fields: Dict[str, str],
        timeout_seconds: int,
        session_id: str,
    ) -> str:
        parts = ['<?xml version="1.0" encoding="windows-1251"?>', "<request>"]

        for field_id, value in fields.items():
            parts.append(f'<field id="{field_id}">{self._xml_escape(str(value))}</field>')

        parts.append(f"<timeout>{int(timeout_seconds)}</timeout>")
        parts.append(f"<sessionID>{self._xml_escape(session_id)}</sessionID>")
        parts.append("</request>")
        return "".join(parts)

    @staticmethod
    def _parse_response_xml(xml_text: str) -> Dict[str, str]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise DualConnectorError(f"XML response parse error: {e}\n{xml_text}") from e

        result: Dict[str, str] = {}
        for child in root:
            if child.tag.lower() == "field":
                field_id = child.attrib.get("id")
                if field_id:
                    result[field_id] = child.text or ""
            else:
                result[child.tag.lower()] = child.text or ""
        return result

    @staticmethod
    def _amount_to_minor_units(amount: Union[int, float, str, Decimal]) -> str:
        amount = Decimal(str(amount))
        if amount < 0:
            raise ValueError(f"Invalid amount: {amount}")

        return str((amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _now_terminal_datetime() -> str:
        return datetime.now().strftime("%Y%m%d%H%M%S")

    @staticmethod
    def _generate_session_id() -> str:
        return f"{int(time.time())}{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _xml_escape(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )


def main():
    client = Tbank()

    # Sale
    result = client.operation(operation_type="sale", amount=1.00)
    print(result.raw_xml)

    # Refund
    result = client.operation(
        operation_type="refund",
        amount=1.00,
    )
    print(result.raw_xml)

    # Short report
    result = client.short_report()
    print(result.raw_xml)

    # Full report
    result = client.full_report()
    print(result.raw_xml)

    # Reconcile totals
    result = client.reconcile_totals()
    print(result.raw_xml)


if __name__ == '__main__':
    main()

