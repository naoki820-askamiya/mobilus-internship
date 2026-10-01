"""
問い合わせルーター: 一覧取得・詳細取得・担当取得・メッセージ取得
"""

from typing import List

from fastapi import APIRouter, Depends, Query

from app.config import DEFAULT_PER_PAGE, MAX_PER_PAGE
from app.middleware.auth_middleware import get_current_operator
from app.models import Operator
from app.repositories.inquiry_repository import InquiryRepository
from app.schemas import InquiryResponse, MessageResponse, PaginatedInquiryResponse
from app.services.inquiry_service import InquiryService

router = APIRouter()
inquiry_service = InquiryService()
inquiry_repository = InquiryRepository()


@router.get("", response_model=PaginatedInquiryResponse)
def list_inquiries(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
    operator: Operator = Depends(get_current_operator),
):
    """問い合わせ一覧取得（ページング付き）"""
    return inquiry_service.list_inquiries(page, per_page, operator.id)


@router.get("/open", response_model=List[InquiryResponse])
def list_open_inquiries(
    operator: Operator = Depends(get_current_operator),
):
    """未完了の問い合わせを優先順で取得"""
    return inquiry_service.list_open(operator.id)


@router.get("/closed", response_model=List[InquiryResponse])
def list_closed_inquiries(
    _operator: Operator = Depends(get_current_operator),
):
    """完了済みの問い合わせを最新分だけ取得"""
    return inquiry_service.list_closed()


@router.get("/{inquiry_id}", response_model=InquiryResponse)
def get_inquiry(
    inquiry_id: int,
    operator: Operator = Depends(get_current_operator),
):
    """問い合わせ詳細取得"""
    inquiry = inquiry_service.get_inquiry(inquiry_id)
    return InquiryService._to_response(inquiry, operator.id)


@router.post("/{inquiry_id}/assign", response_model=InquiryResponse)
def assign_inquiry(
    inquiry_id: int,
    operator: Operator = Depends(get_current_operator),
):
    """問い合わせ担当取得"""
    inquiry = inquiry_service.assign_operator(inquiry_id, operator.id)
    return InquiryService._to_response(inquiry, operator.id)


@router.get("/{inquiry_id}/messages", response_model=List[MessageResponse])
def get_inquiry_messages(
    inquiry_id: int,
    _operator: Operator = Depends(get_current_operator),
):
    """問い合わせのメッセージ一覧取得"""
    # 問い合わせ存在確認
    inquiry_service.get_inquiry(inquiry_id)

    messages = inquiry_repository.find_messages_by_inquiry_id(inquiry_id)
    return [
        MessageResponse(
            id=msg.id,
            inquiry_id=msg.inquiry_id,
            sender_type=msg.sender_type,
            sender_name=msg.sender_name,
            content=msg.content,
            created_at=msg.created_at,
        )
        for msg in messages
    ]
