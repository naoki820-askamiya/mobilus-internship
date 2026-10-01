"""
待ち時間APIのテスト
"""

import sqlite3
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import CREATE_TABLES_SQL
from app.main import app
from app.models import InquiryStatus, OperatorAvailabilityStatus
from app.repositories.auth_repository import AuthRepository
from app.repositories.inquiry_repository import InquiryRepository
from app.schemas import HourlyWaitTimeItem, HourlyWaitTimeResponse, WaitTimeResponse
from app.services.wait_time_service import WaitTimeService


class TestWaitTimeCalculation:
    """推定待ち時間の計算テスト"""

    @pytest.mark.parametrize(
        ("active_count", "waiting_count", "operator_count", "expected"),
        [
            (0, 0, 1, 0),
            (1, 0, 1, 0),
            (2, 0, 1, 0),
            (2, 2, 1, 5),
            (0, 3, 1, 3),
            (4, 2, 2, 3),
        ],
    )
    def test_calculates_and_rounds_up(
        self,
        active_count: int,
        waiting_count: int,
        operator_count: int,
        expected: int,
    ):
        """総負荷とキャパシティの差から待ち時間を分単位で切り上げる"""
        result = WaitTimeService._calculate_estimated_wait_minutes(
            active_count,
            waiting_count,
            operator_count,
        )
        assert result == expected

    def test_returns_none_when_no_active_operators(self):
        """有効なオペレータが0人の場合は待ち時間を算出しない"""
        result = WaitTimeService._calculate_estimated_wait_minutes(2, 3, 0)
        assert result is None


class TestWaitTimeService:
    """待ち時間サービスのテスト"""

    @patch("app.services.wait_time_service.now_jst")
    def test_uses_same_timestamp_for_count_and_response(self, mock_now_jst):
        """セッション判定とレスポンスに同じ基準時刻を使う"""
        updated_at = "2026-08-17 18:30:00"
        mock_now_jst.return_value = updated_at
        service = WaitTimeService()
        service.inquiry_repository = MagicMock()
        service.auth_repository = MagicMock()
        service.inquiry_repository.count_active.return_value = 2
        service.inquiry_repository.count_waiting.return_value = 2
        service.auth_repository.count_active_operators.return_value = 1

        result = service.get_current_wait_time()

        assert result == WaitTimeResponse(
            estimated_wait_minutes=5,
            updated_at=updated_at,
        )
        service.inquiry_repository.count_active.assert_called_once_with()
        service.inquiry_repository.count_waiting.assert_called_once_with()
        service.auth_repository.count_active_operators.assert_called_once_with(updated_at)

    @patch("app.services.wait_time_service.now_jst")
    def test_generates_previous_day_hourly_wait_times(self, mock_now_jst):
        """取得日前日の8時から18時までをピーク時間帯込みで生成する"""
        mock_now_jst.return_value = "2026-08-17 18:30:00"
        service = WaitTimeService()

        result = service.get_hourly_wait_times()

        assert result.updated_at == "2026-08-17 18:30:00"
        assert result.items == [
            HourlyWaitTimeItem(
                time=f"2026-08-16 {hour:02d}:00:00",
                estimated_wait_minutes=wait_minutes,
            )
            for hour, wait_minutes in [
                (8, 2),
                (9, 8),
                (10, 12),
                (11, 15),
                (12, 10),
                (13, 5),
                (14, 4),
                (15, 6),
                (16, 12),
                (17, 9),
                (18, 3),
            ]
        ]
        wait_minutes_by_hour = {
            int(item.time[11:13]): item.estimated_wait_minutes for item in result.items
        }
        peak_hours = {9, 10, 11, 12, 16, 17}
        peak_wait_times = [
            wait_minutes
            for hour, wait_minutes in wait_minutes_by_hour.items()
            if hour in peak_hours
        ]
        regular_wait_times = [
            wait_minutes
            for hour, wait_minutes in wait_minutes_by_hour.items()
            if hour not in peak_hours
        ]
        assert min(peak_wait_times) > max(regular_wait_times)

    @patch("app.services.wait_time_service.now_jst")
    def test_generates_previous_day_across_year_boundary(self, mock_now_jst):
        """年初の取得でも前年末の日付を正しく生成する"""
        mock_now_jst.return_value = "2026-01-01 00:30:00"

        result = WaitTimeService().get_hourly_wait_times()

        assert result.items[0].time == "2025-12-31 08:00:00"
        assert result.items[-1].time == "2025-12-31 18:00:00"
        assert len(result.items) == 11


class TestWaitTimeRepositories:
    """待ち時間計算用の集計クエリのテスト"""

    @patch("app.repositories.inquiry_repository.get_db")
    def test_count_waiting_filters_unassigned_inquiries(self, mock_get_db):
        """待機中かつ未割り当ての問い合わせのみを数える"""
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = (4,)
        mock_get_db.return_value.__enter__.return_value = connection

        result = InquiryRepository().count_waiting()

        assert result == 4
        query, parameters = connection.execute.call_args.args
        assert "status = ?" in query
        assert "assigned_operator_id IS NULL" in query
        assert parameters == (InquiryStatus.WAITING,)

    @patch("app.repositories.inquiry_repository.get_db")
    def test_count_active_filters_active_inquiries(self, mock_get_db):
        """対応中の問い合わせのみを数える"""
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = (3,)
        mock_get_db.return_value.__enter__.return_value = connection

        result = InquiryRepository().count_active()

        assert result == 3
        query, parameters = connection.execute.call_args.args
        assert "status = ?" in query
        assert parameters == (InquiryStatus.ACTIVE,)

    @patch("app.repositories.auth_repository.get_db")
    def test_count_active_operators_uses_distinct_sessions(self, mock_get_db):
        """複数の有効セッションを持つ同一オペレータを重複集計しない"""
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = (2,)
        mock_get_db.return_value.__enter__.return_value = connection
        updated_at = "2026-08-17 18:30:00"

        result = AuthRepository().count_active_operators(updated_at)

        assert result == 2
        query, parameters = connection.execute.call_args.args
        assert "COUNT(DISTINCT sessions.operator_id)" in query
        assert "INNER JOIN operators" in query
        assert "sessions.expires_at > ?" in query
        assert "operators.availability_status = ?" in query
        assert parameters == (
            updated_at,
            OperatorAvailabilityStatus.AVAILABLE,
        )

    def test_count_active_operators_filters_status_and_sessions(self):
        """稼働中かつ有効なセッションを持つオペレータだけを数える"""
        connection = sqlite3.connect(":memory:")
        connection.executescript(CREATE_TABLES_SQL)
        connection.executemany(
            """INSERT INTO operators
               (id, username, password_hash, display_name, availability_status, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (1, "available", "hash", "稼働", OperatorAvailabilityStatus.AVAILABLE, "now"),
                (2, "away", "hash", "離席", OperatorAvailabilityStatus.AWAY, "now"),
                (
                    3,
                    "no-session",
                    "hash",
                    "セッションなし",
                    OperatorAvailabilityStatus.AVAILABLE,
                    "now",
                ),
                (
                    4,
                    "expired",
                    "hash",
                    "期限切れ",
                    OperatorAvailabilityStatus.AVAILABLE,
                    "now",
                ),
            ],
        )
        connection.executemany(
            """INSERT INTO sessions (id, operator_id, created_at, expires_at)
               VALUES (?, ?, ?, ?)""",
            [
                ("available-1", 1, "2026-08-17 09:00:00", "2026-08-17 20:00:00"),
                ("available-2", 1, "2026-08-17 10:00:00", "2026-08-17 21:00:00"),
                ("away", 2, "2026-08-17 09:00:00", "2026-08-17 20:00:00"),
                ("expired", 4, "2026-08-17 09:00:00", "2026-08-17 18:00:00"),
            ],
        )

        @contextmanager
        def get_test_db():
            yield connection

        try:
            with patch(
                "app.repositories.auth_repository.get_db",
                side_effect=get_test_db,
            ):
                result = AuthRepository().count_active_operators("2026-08-17 18:30:00")
        finally:
            connection.close()

        assert result == 1


def test_get_wait_time_api_response():
    """待ち時間APIが仕様どおりのレスポンスを返す"""
    expected = WaitTimeResponse(
        estimated_wait_minutes=5,
        updated_at="2026-08-17 18:30:00",
    )
    with patch(
        "app.routers.wait_time.wait_time_service.get_current_wait_time",
        return_value=expected,
    ):
        response = TestClient(app).get("/api/wait-time")

    assert response.status_code == 200
    assert response.json() == {
        "estimated_wait_minutes": 5,
        "updated_at": "2026-08-17 18:30:00",
    }


def test_get_hourly_wait_times_api_response():
    """待ち時間時系列APIが仕様どおりのレスポンスを返す"""
    expected = HourlyWaitTimeResponse(
        updated_at="2026-08-17 18:30:00",
        items=[
            HourlyWaitTimeItem(
                time="2026-08-16 08:00:00",
                estimated_wait_minutes=2,
            ),
            HourlyWaitTimeItem(
                time="2026-08-16 09:00:00",
                estimated_wait_minutes=8,
            ),
        ],
    )
    with patch(
        "app.routers.wait_time.wait_time_service.get_hourly_wait_times",
        return_value=expected,
    ):
        response = TestClient(app).get("/api/wait-time/hourly")

    assert response.status_code == 200
    assert response.json() == {
        "updated_at": "2026-08-17 18:30:00",
        "items": [
            {
                "time": "2026-08-16 08:00:00",
                "estimated_wait_minutes": 2,
            },
            {
                "time": "2026-08-16 09:00:00",
                "estimated_wait_minutes": 8,
            },
        ],
    }
