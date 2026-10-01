"""
Pydantic スキーマ（リクエスト/レスポンス定義）
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models import DisplayStatus

# === 認証 ===


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class OperatorResponse(BaseModel):
    id: int
    username: str
    display_name: str


class CurrentOperatorResponse(OperatorResponse):
    availability_status: int = Field(..., ge=0, le=1)


class OperatorAvailabilityUpdateRequest(BaseModel):
    availability_status: int = Field(..., ge=0, le=1)


# === 問い合わせ ===


class InquiryResponse(BaseModel):
    id: int
    status: int
    assigned_operator_id: Optional[int]
    created_at: str
    closed_at: Optional[str]
    bot_state: Optional[str] = None
    display_status: Optional[DisplayStatus] = None  # フロント表示用


class PaginatedInquiryResponse(BaseModel):
    items: List[InquiryResponse]
    page: int
    per_page: int
    total: int
    total_pages: int


# === 待ち時間 ===


class WaitTimeResponse(BaseModel):
    estimated_wait_minutes: Optional[int]
    updated_at: str


class HourlyWaitTimeItem(BaseModel):
    time: str
    estimated_wait_minutes: int


class HourlyWaitTimeResponse(BaseModel):
    updated_at: str
    items: List[HourlyWaitTimeItem]


# === メッセージ ===


class MessageResponse(BaseModel):
    id: int
    inquiry_id: int
    sender_type: int
    sender_name: Optional[str]
    content: str
    created_at: str


# === サマリーボード ===


class HourlySummaryResponse(BaseModel):
    hour: int
    session_count: int
    average_first_response_seconds: Optional[int]


class DailySummaryResponse(BaseModel):
    date: date
    total_sessions: int
    average_first_response_seconds: Optional[int]
    hourly: List[HourlySummaryResponse]
# === BOT事前質問 ===


class BotOptionResponse(BaseModel):
    value: str
    label: str


class BotQuestionResponse(BaseModel):
    message_id: int
    state: str
    type: str
    text: str
    options: List[BotOptionResponse]


class BotStepResponse(BaseModel):
    """BOT開始・BOT回答で共通のレスポンス"""

    inquiry_id: int
    result: str  # QUESTION / OPERATOR / COMPLETED
    messages: List[MessageResponse]  # 今回追加されたメッセージ（時系列順）
    question: Optional[BotQuestionResponse] = None  # resultがQUESTIONのときのみ


class BotAnswerPayload(BaseModel):
    type: str  # CHOICE / SIZE
    value: Optional[str] = None  # type=CHOICE のとき必須
    length_cm: Optional[int] = None  # type=SIZE のとき必須（縦）
    width_cm: Optional[int] = None  # type=SIZE のとき必須（横）
    height_cm: Optional[int] = None  # type=SIZE のとき必須（高さ）


class BotAnswerRequest(BaseModel):
    state: str  # 回答対象の質問状態（DBの値と一致しない場合は拒否する）
    answer: BotAnswerPayload


# === オペレータ管理 ===


class OperatorCreateRequest(BaseModel):
    username: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)


class OperatorCreateResponse(BaseModel):
    operator: OperatorResponse
    generated_password: str
