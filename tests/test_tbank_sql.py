"""Tests for T-Bank SQLite storage."""

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from tbank_sql import save_tbank_sale


class TbankSalesDBTest(unittest.TestCase):
    """Verify creation and insertion of successful T-Bank sales."""

    def test_save_tbank_sale_creates_table_and_inserts_values(self):
        """Save exact receipt values in the documented table format."""
        receipt = {
            "date_create": "20260724",
            "number_receipt": "256736/01",
            "sum-cashless": 1699.0,
        }

        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "tbank.db"
            with patch.dict(os.environ, {"tbank_sql_path": str(db_path)}):
                save_tbank_sale(receipt, "620412740441")

            with closing(sqlite3.connect(db_path)) as connection:
                columns = connection.execute("PRAGMA table_info(tbank)").fetchall()
                row = connection.execute(
                    "SELECT id, date, sbis_id, tbank_id, summ FROM tbank"
                ).fetchone()

        self.assertEqual(
            [column[1] for column in columns],
            ["id", "date", "sbis_id", "tbank_id", "summ"],
        )
        self.assertEqual(row, (1, "2026-07-24", "256736/01", "620412740441", 1699))


if __name__ == "__main__":
    unittest.main()
