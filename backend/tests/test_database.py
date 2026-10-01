"""
データベーススキーマのテスト
"""

import sqlite3

import pytest

from app.database import CREATE_TABLES_SQL
from app.models import Operator, OperatorAvailabilityStatus


def test_operator_availability_schema_constraints():
    """稼働状態の安全な初期値と値域をDB制約で保証する"""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(CREATE_TABLES_SQL)

    try:
        connection.execute(
            """INSERT INTO operators
               (username, password_hash, display_name, created_at)
               VALUES (?, ?, ?, ?)""",
            ("admin", "hash", "管理者", "2026-08-19 09:00:00"),
        )
        row = connection.execute(
            "SELECT * FROM operators WHERE username = ?",
            ("admin",),
        ).fetchone()
        operator = Operator(**dict(row))

        assert operator.availability_status == OperatorAvailabilityStatus.AWAY

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """INSERT INTO operators
                   (username, password_hash, display_name, availability_status, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                ("invalid", "hash", "不正状態", 2, "2026-08-19 09:00:00"),
            )

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """INSERT INTO operators
                   (username, password_hash, display_name, availability_status, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                ("null", "hash", "状態なし", None, "2026-08-19 09:00:00"),
            )
    finally:
        connection.close()
