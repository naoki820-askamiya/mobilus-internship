"""
待ち時間ルーター: 現在の推定待ち時間を取得
"""

from fastapi import APIRouter

from app.schemas import HourlyWaitTimeResponse, WaitTimeResponse
from app.services.wait_time_service import WaitTimeService

router = APIRouter()
wait_time_service = WaitTimeService()


@router.get("", response_model=WaitTimeResponse)
def get_wait_time():
    """現在の推定待ち時間を取得"""
    return wait_time_service.get_current_wait_time()


@router.get("/hourly", response_model=HourlyWaitTimeResponse)
def get_hourly_wait_times():
    """取得日前日の1時間ごとの推定待ち時間を取得"""
    return wait_time_service.get_hourly_wait_times()
