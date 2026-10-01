"""
サマリーリポジトリ: 指定日に開始した問い合わせと初回応答の取得
"""

from datetime import date, timedelta
from typing import List

from app.database import get_db
from app.models import InquiryFirstResponse, SenderType


class SummaryRepository:
    """サマリーボード用集計データのアクセス"""

    def find_inquiries_with_first_response(
        self, selected_date: date
    ) -> List[InquiryFirstResponse]:
        """指定日に開始した問い合わせと最初のオペレータ応答を取得"""
        start_at = selected_date.strftime("%Y-%m-%d 00:00:00")
        end_at = (selected_date + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")

        with get_db() as conn:
            rows = conn.execute(
                """SELECT
                       i.id,
                       i.created_at,
                       MIN(m.created_at) AS first_response_at
                   FROM inquiries AS i
                   LEFT JOIN messages AS m
                       ON m.inquiry_id = i.id
                       AND m.sender_type = ?
                   WHERE i.created_at >= ?
                     AND i.created_at < ?
                   GROUP BY i.id, i.created_at
                   ORDER BY i.created_at ASC, i.id ASC""",
                (SenderType.OPERATOR, start_at, end_at),
            ).fetchall()
            return [InquiryFirstResponse(**dict(row)) for row in rows]
