from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional
from xml.etree import ElementTree as ET

import requests


# ====== НАСТРОЙКИ ======
DC_SERVICE_URL = "http://127.0.0.1:9015"
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_CURRENCY_CODE = "643"  # RUB


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


class DualConnectorClient:
    def __init__(
        self,
        base_url: str = DC_SERVICE_URL,
        default_terminal_id: Optional[str] = None,
        encoding: str = "windows-1251",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_terminal_id = default_terminal_id
        self.encoding = encoding

    # =========================
    # ПУБЛИЧНЫЕ МЕТОДЫ
    # =========================

    def sale(
        self,
        receipt_json_path: str,
        terminal_id: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        include_receipt_field_90: bool = False,
    ) -> OperationResult:
        receipt = self._load_receipt_json(receipt_json_path)
        amount_minor = self._receipt_amount_to_minor_units(receipt)

        fields = {
            "00": amount_minor,
            "04": DEFAULT_CURRENCY_CODE,
            "21": self._now_terminal_datetime(),
            "25": OperationCode.SALE,
        }

        effective_terminal_id = terminal_id or self.default_terminal_id
        if effective_terminal_id:
            fields["27"] = effective_terminal_id

        if include_receipt_field_90:
            fields["90"] = self._build_receipt_print_text(receipt)

        return self._send_request(fields, timeout_seconds)

    def refund(
        self,
        receipt_json_path: str,
        terminal_id: Optional[str] = None,
        original_reference_number: Optional[str] = None,
        original_authorization_code: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        include_receipt_field_90: bool = False,
    ) -> OperationResult:
        receipt = self._load_receipt_json(receipt_json_path)
        amount_minor = self._receipt_amount_to_minor_units(receipt)

        fields = {
            "00": amount_minor,
            "04": DEFAULT_CURRENCY_CODE,
            "21": self._now_terminal_datetime(),
            "25": OperationCode.REFUND,
        }

        effective_terminal_id = terminal_id or self.default_terminal_id
        if effective_terminal_id:
            fields["27"] = effective_terminal_id

        # Эти поля для возврата часто нужны, но зависят от настройки терминала/хоста
        if original_reference_number:
            fields["14"] = original_reference_number

        if original_authorization_code:
            fields["13"] = original_authorization_code

        if include_receipt_field_90:
            fields["90"] = self._build_receipt_print_text(receipt)

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

        effective_terminal_id = terminal_id or self.default_terminal_id
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
        Операция 63: выполнение пользовательской команды.
        Код подкоманды кладём в поле 80.
        """
        fields = {
            "04": DEFAULT_CURRENCY_CODE,
            "21": self._now_terminal_datetime(),
            "25": OperationCode.USER_COMMAND,
            "80": str(command_code),
        }

        effective_terminal_id = terminal_id or self.default_terminal_id
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
        Операция 63 / команда 22.
        Формат дополнительных полей для копии чека зависит от настроек банка.
        Ниже безопасный каркас:
        - 80 = 22
        - 81 = номер чека
        - 06 или 21 можно использовать под дату, если это ожидает ваш хост
        """
        fields = {
            "04": DEFAULT_CURRENCY_CODE,
            "21": self._now_terminal_datetime(),
            "25": OperationCode.USER_COMMAND,
            "80": UserCommandCode.RECEIPT_COPY,
            "81": receipt_number,
        }

        if receipt_date:
            fields["06"] = receipt_date  # YYYYMMDDHHMMSS, если требуется хостом

        effective_terminal_id = terminal_id or self.default_terminal_id
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
    # ВНУТРЕННИЕ МЕТОДЫ
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
            raise DualConnectorError(f"Ошибка парсинга XML ответа: {e}\n{xml_text}") from e

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
    def _load_receipt_json(path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="windows-1251") as f:
            return json.load(f)

    @staticmethod
    def _receipt_amount_to_minor_units(receipt: Dict[str, Any]) -> str:
        if "sum-cashless" not in receipt:
            raise ValueError("В JSON нет ключа 'sum-cashless'")

        amount = Decimal(str(receipt["sum-cashless"]))
        if amount <= 0:
            raise ValueError(f"Некорректная сумма: {amount}")

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

    @staticmethod
    def _build_receipt_print_text(receipt: Dict[str, Any]) -> str:
        lines = [
            f"Чек № {receipt.get('number_receipt', '')}",
            f"Дата: {receipt.get('sdate', '')} {receipt.get('stime', '')}",
        ]
        for item in receipt.get("items", []):
            lines.append(str(item.get("name", "")).strip())
            lines.append(f"{item.get('quantity', 1)} x {item.get('price', 0)}")
        lines.append(f"ИТОГО БЕЗНАЛ: {receipt.get('sum-cashless', 0)}")
        return "\n".join(lines)


def main():
    client = DualConnectorClient(
        base_url="http://127.0.0.1:9015",
        default_terminal_id="10736528",
    )

    # # Продажа из вашего JSON
    # result = client.sale("d:\\files\\CK256885_01_sale.json")
    # print(result.raw_xml)
    #
    # # Возврат
    # result = client.refund(
    #     "d:\\files\\CK256885_01_sale.json",
    #     original_reference_number="123456789012",
    #     original_authorization_code="A1B2C3",
    # )
    # print(result.raw_xml)

    # # Краткий отчет
    # result = client.short_report()
    # print(result.raw_xml)
    #
    # # Полный отчет
    # result = client.full_report()
    # print(result.raw_xml)

    # Сверка итогов
    result = client.reconcile_totals()
    print(result.raw_xml)


    # Копия чека
    result = client.receipt_copy(
        receipt_number="256885/01",
        receipt_date="20260413114930",
    )
    print(result.raw_xml)

if __name__ == '__main__':
    main()