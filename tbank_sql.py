"""SQLite storage for successful T-Bank sales."""

import logging
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).with_name(".env"))

CREATE_TBANK_TABLE = """
CREATE TABLE IF NOT EXISTS tbank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    sbis_id TEXT NOT NULL,
    tbank_id TEXT NOT NULL,
    summ NUMERIC NOT NULL
)
"""


class TbankSalesDB:
    """Store successful T-Bank sales in SQLite."""

    def __init__(self, db_path: str):
        """Initialize storage and create the ``tbank`` table.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(CREATE_TBANK_TABLE)

    def _connect(self) -> sqlite3.Connection:
        """Return a connection to the configured SQLite database."""
        return sqlite3.connect(self.db_path)

    def add_sale(self, date: str, sbis_id: str, tbank_id: str, summ: object) -> None:
        """Save one successful T-Bank sale.

        Args:
            date: Receipt date in ``YYYY-MM-DD`` format.
            sbis_id: Receipt number in SBIS.
            tbank_id: T-Bank reference number.
            summ: Sale amount in rubles.
        """
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO tbank (date, sbis_id, tbank_id, summ) VALUES (?, ?, ?, ?)",
                    (date, sbis_id, tbank_id, summ),
                )


def save_tbank_sale(receipt: Mapping[str, object], reference_number: str) -> None:
    """Save a successful T-Bank sale using receipt and environment data.

    Args:
        receipt: Cash receipt data from SBIS.
        reference_number: Reference number returned by T-Bank.

    Raises:
        KeyError: If required receipt fields are missing.
        ValueError: If the database path or reference number is empty.
        sqlite3.Error: If the database cannot be created or updated.
    """
    db_path = os.getenv("tbank_sql_path")
    if not db_path:
        raise ValueError("tbank_sql_path is not configured")
    if not reference_number:
        raise ValueError("T-Bank reference number is empty")

    receipt_date = datetime.strptime(str(receipt["date_create"]), "%Y%m%d").strftime("%Y-%m-%d")
    TbankSalesDB(db_path).add_sale(
        date=receipt_date,
        sbis_id=str(receipt["number_receipt"]),
        tbank_id=reference_number,
        summ=receipt["sum-cashless"],
    )
