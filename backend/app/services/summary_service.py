"""
サマリーサービス: 日次・時間帯別の問い合わせ集計
"""

from datetime import date, datetime
from typing import List, Optional

from app.models import InquiryFirstResponse
from app.repositories.summary_repository import SummaryRepository
from app.schemas import DailySummaryResponse, HourlySummaryResponse

HOURS_PER_DAY = 24
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


class SummaryService:
    """サマリーボードの集計ロジック"""

    def __init__(self):
        self.repository = SummaryRepository()

    def get_daily_summary(self, selected_date: date) -> DailySummaryResponse:
        """指定日のセッション数と初回応答時間を集計"""
        inquiries = self.repository.find_inquiries_with_first_response(selected_date)
        session_counts = [0] * HOURS_PER_DAY
        response_seconds_by_hour: List[List[int]] = [
            [] for _ in range(HOURS_PER_DAY)
        ]

        for inquiry in inquiries:
            created_at = datetime.strptime(inquiry.created_at, TIMESTAMP_FORMAT)
            session_counts[created_at.hour] += 1

            response_seconds = self._calculate_first_response_seconds(inquiry)
            if response_seconds is not None:
                response_seconds_by_hour[created_at.hour].append(response_seconds)

        all_response_seconds = [
            response_seconds
            for hourly_response_seconds in response_seconds_by_hour
            for response_seconds in hourly_response_seconds
        ]
        hourly = [
            HourlySummaryResponse(
                hour=hour,
                session_count=session_counts[hour],
                average_first_response_seconds=self._average(
                    response_seconds_by_hour[hour]
                ),
            )
            for hour in range(HOURS_PER_DAY)
        ]

        return DailySummaryResponse(
            date=selected_date,
            total_sessions=len(inquiries),
            average_first_response_seconds=self._average(all_response_seconds),
            hourly=hourly,
        )

    @staticmethod
    def _calculate_first_response_seconds(
        inquiry: InquiryFirstResponse,
    ) -> Optional[int]:
        """問い合わせ作成から最初のオペレータ応答までの秒数を算出"""
        if inquiry.first_response_at is None:
            return None

        created_at = datetime.strptime(inquiry.created_at, TIMESTAMP_FORMAT)
        first_response_at = datetime.strptime(
            inquiry.first_response_at, TIMESTAMP_FORMAT
        )
        return round((first_response_at - created_at).total_seconds())

    @staticmethod
    def _average(values: List[int]) -> Optional[int]:
        """値がない場合は未集計としてNoneを返す"""
        if not values:
            return None
        return round(sum(values) / len(values))
