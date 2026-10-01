"""
待ち時間サービス: 現在の推定待ち時間を算出
"""

from datetime import datetime, timedelta
from typing import Optional

from app.config import (
    CONCURRENT_INQUIRIES_PER_OPERATOR,
    ESTIMATED_MINUTES_PER_INQUIRY,
    HOURLY_WAIT_TIME_END_HOUR,
    HOURLY_WAIT_TIME_MINUTES_BY_HOUR,
    HOURLY_WAIT_TIME_START_HOUR,
)
from app.database import now_jst
from app.repositories.auth_repository import AuthRepository
from app.repositories.inquiry_repository import InquiryRepository
from app.schemas import HourlyWaitTimeItem, HourlyWaitTimeResponse, WaitTimeResponse

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class WaitTimeService:
    """待ち時間の算出ロジック"""

    def __init__(self):
        self.inquiry_repository = InquiryRepository()
        self.auth_repository = AuthRepository()

    def get_current_wait_time(self) -> WaitTimeResponse:
        """現在の推定待ち時間と算出時刻を取得"""
        updated_at = now_jst()
        active_count = self.inquiry_repository.count_active()
        waiting_count = self.inquiry_repository.count_waiting()
        operator_count = self.auth_repository.count_active_operators(updated_at)
        estimated_wait_minutes = self._calculate_estimated_wait_minutes(
            active_count,
            waiting_count,
            operator_count,
        )
        return WaitTimeResponse(
            estimated_wait_minutes=estimated_wait_minutes,
            updated_at=updated_at,
        )

    def get_hourly_wait_times(self) -> HourlyWaitTimeResponse:
        """取得日前日の営業時間帯について、1時間ごとの待ち時間を取得"""
        updated_at = now_jst()
        current_datetime = datetime.strptime(updated_at, DATETIME_FORMAT)
        target_start = current_datetime.replace(
            hour=HOURLY_WAIT_TIME_START_HOUR,
            minute=0,
            second=0,
            microsecond=0,
        ) - timedelta(days=1)
        item_count = HOURLY_WAIT_TIME_END_HOUR - HOURLY_WAIT_TIME_START_HOUR + 1
        items = [
            HourlyWaitTimeItem(
                time=(target_start + timedelta(hours=hour_offset)).strftime(DATETIME_FORMAT),
                estimated_wait_minutes=HOURLY_WAIT_TIME_MINUTES_BY_HOUR[
                    HOURLY_WAIT_TIME_START_HOUR + hour_offset
                ],
            )
            for hour_offset in range(item_count)
        ]
        return HourlyWaitTimeResponse(updated_at=updated_at, items=items)

    @staticmethod
    def _calculate_estimated_wait_minutes(
        active_count: int,
        waiting_count: int,
        operator_count: int,
    ) -> Optional[int]:
        """対応中・待機中の件数とオペレータ数から推定待ち時間を算出"""
        if operator_count == 0:
            return None

        load = active_count + waiting_count
        capacity = operator_count * CONCURRENT_INQUIRIES_PER_OPERATOR
        if capacity > load:
            return 0

        excess_load = load - capacity
        numerator = excess_load * ESTIMATED_MINUTES_PER_INQUIRY
        return (numerator + capacity - 1) // capacity
