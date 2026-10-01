"""
サマリールーター: 指定日の問い合わせ集計取得
"""

from datetime import date

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import get_current_operator
from app.models import Operator
from app.schemas import DailySummaryResponse
from app.services.summary_service import SummaryService

router = APIRouter()
summary_service = SummaryService()


@router.get("", response_model=DailySummaryResponse)
def get_summary(
    date: date,
    _operator: Operator = Depends(get_current_operator),
):
    """指定日のセッション数と初回応答時間を取得"""
    return summary_service.get_daily_summary(date)
