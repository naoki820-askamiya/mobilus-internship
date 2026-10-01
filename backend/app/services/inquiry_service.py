"""
問い合わせサービス: 一覧取得・担当割り当て・ステータス算出
"""

import math

from fastapi import HTTPException

from app.config import CLOSED_INQUIRY_DISPLAY_LIMIT
from app.models import DISPLAY_STATUS_PRIORITY, DisplayStatus, Inquiry, InquiryStatus
from app.repositories.inquiry_repository import InquiryRepository
from app.schemas import InquiryResponse, PaginatedInquiryResponse


class InquiryService:
    """問い合わせ管理のビジネスロジック"""

    def __init__(self):
        self.repository = InquiryRepository()

    def list_inquiries(
        self, page: int, per_page: int, operator_id: int
    ) -> PaginatedInquiryResponse:
        """問い合わせ一覧を取得（表示ステータス付き）"""
        inquiries, total = self.repository.find_all(page, per_page)
        total_pages = math.ceil(total / per_page) if per_page > 0 else 0

        items = [self._to_response(inquiry, operator_id) for inquiry in inquiries]

        return PaginatedInquiryResponse(
            items=items,
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        )

    def list_open(self, operator_id: int) -> list[InquiryResponse]:
        """未完了の問い合わせをオペレータ視点の優先順で取得"""
        inquiries = self.repository.find_open()
        inquiries.sort(
            key=lambda inquiry: (
                DISPLAY_STATUS_PRIORITY.index(
                    self._compute_display_status(inquiry, operator_id)
                ),
                inquiry.created_at,
                inquiry.id,
            )
        )
        return [self._to_response(inquiry, operator_id) for inquiry in inquiries]

    def list_closed(self) -> list[InquiryResponse]:
        """完了済みの問い合わせを設定件数まで取得"""
        inquiries = self.repository.find_recent_closed(CLOSED_INQUIRY_DISPLAY_LIMIT)
        return [self._to_response(inquiry) for inquiry in inquiries]

    def get_inquiry(self, inquiry_id: int) -> Inquiry:
        """問い合わせ詳細を取得"""
        inquiry = self.repository.find_by_id(inquiry_id)
        if inquiry is None:
            raise HTTPException(status_code=404, detail="問い合わせが見つかりません")
        return inquiry

    def assign_operator(self, inquiry_id: int, operator_id: int) -> Inquiry:
        """問い合わせに担当者を割り当て（排他制御）"""
        success = self.repository.update_assignment(inquiry_id, operator_id)
        if not success:
            raise HTTPException(
                status_code=409,
                detail="この問い合わせは既に他のオペレータが担当しています",
            )
        inquiry = self.repository.find_by_id(inquiry_id)
        if inquiry is None:
            raise HTTPException(status_code=404, detail="問い合わせが見つかりません")
        return inquiry

    @staticmethod
    def _compute_display_status(inquiry: Inquiry, operator_id: int) -> DisplayStatus:
        """オペレータの視点で表示ステータスを算出"""
        if inquiry.status == InquiryStatus.CLOSED:
            return DisplayStatus.CLOSED
        elif inquiry.status == InquiryStatus.BOT:
            return DisplayStatus.BOT
        elif inquiry.status == InquiryStatus.WAITING:
            return DisplayStatus.WAITING
        elif inquiry.assigned_operator_id == operator_id:
            return DisplayStatus.MINE
        else:
            return DisplayStatus.OTHERS

    @classmethod
    def _to_response(
        cls, inquiry: Inquiry, operator_id: int | None = None
    ) -> InquiryResponse:
        """問い合わせをAPIレスポンスへ変換"""
        display_status = (
            DisplayStatus.CLOSED
            if operator_id is None
            else cls._compute_display_status(inquiry, operator_id)
        )
        return InquiryResponse(
            id=inquiry.id,
            status=inquiry.status,
            assigned_operator_id=inquiry.assigned_operator_id,
            created_at=inquiry.created_at,
            closed_at=inquiry.closed_at,
            bot_state=inquiry.bot_state,
            display_status=display_status,
        )
