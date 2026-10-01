"""サマリーサービスの集計テスト"""

from datetime import date
from unittest.mock import patch

from app.models import InquiryFirstResponse
from app.services.summary_service import HOURS_PER_DAY, SummaryService

SELECTED_DATE = date(2026, 8, 18)


class TestSummaryService:
    """日次・時間帯別集計のテスト"""

    @patch("app.services.summary_service.SummaryRepository")
    def test_aggregates_sessions_and_first_response_times(
        self, mock_repository_class
    ):
        """未応答を件数に含め、応答時間の平均から除外する"""
        mock_repository = mock_repository_class.return_value
        mock_repository.find_inquiries_with_first_response.return_value = [
            InquiryFirstResponse(
                id=1,
                created_at="2026-08-18 09:00:00",
                first_response_at="2026-08-18 09:01:30",
            ),
            InquiryFirstResponse(
                id=2,
                created_at="2026-08-18 09:30:00",
                first_response_at=None,
            ),
            InquiryFirstResponse(
                id=3,
                created_at="2026-08-18 10:00:00",
                first_response_at="2026-08-18 10:00:30",
            ),
        ]
        service = SummaryService()
        service.repository = mock_repository

        result = service.get_daily_summary(SELECTED_DATE)

        assert result.total_sessions == 3
        assert result.average_first_response_seconds == 60
        assert len(result.hourly) == HOURS_PER_DAY
        assert result.hourly[9].session_count == 2
        assert result.hourly[9].average_first_response_seconds == 90
        assert result.hourly[10].session_count == 1
        assert result.hourly[10].average_first_response_seconds == 30
        mock_repository.find_inquiries_with_first_response.assert_called_once_with(
            SELECTED_DATE
        )

    @patch("app.services.summary_service.SummaryRepository")
    def test_returns_empty_twenty_four_hour_summary(self, mock_repository_class):
        """問い合わせがない日も24時間分の空データを返す"""
        mock_repository = mock_repository_class.return_value
        mock_repository.find_inquiries_with_first_response.return_value = []
        service = SummaryService()
        service.repository = mock_repository

        result = service.get_daily_summary(SELECTED_DATE)

        assert result.total_sessions == 0
        assert result.average_first_response_seconds is None
        assert [item.hour for item in result.hourly] == list(range(HOURS_PER_DAY))
        assert all(item.session_count == 0 for item in result.hourly)
        assert all(
            item.average_first_response_seconds is None for item in result.hourly
        )

    @patch("app.services.summary_service.SummaryRepository")
    def test_returns_none_when_all_sessions_are_unanswered(
        self, mock_repository_class
    ):
        """全問い合わせが未応答なら平均初回応答時間を返さない"""
        mock_repository = mock_repository_class.return_value
        mock_repository.find_inquiries_with_first_response.return_value = [
            InquiryFirstResponse(
                id=1,
                created_at="2026-08-18 15:00:00",
                first_response_at=None,
            )
        ]
        service = SummaryService()
        service.repository = mock_repository

        result = service.get_daily_summary(SELECTED_DATE)

        assert result.total_sessions == 1
        assert result.average_first_response_seconds is None
        assert result.hourly[15].average_first_response_seconds is None
