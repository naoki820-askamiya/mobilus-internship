"""
データモデル定義（データクラス）
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass
class Operator:
    """オペレータ"""

    id: int
    username: str
    password_hash: str
    display_name: str
    availability_status: int
    created_at: str


@dataclass
class Session:
    """ログインセッション"""

    id: str
    operator_id: int
    created_at: str
    expires_at: str


@dataclass
class Inquiry:
    """問い合わせ"""

    id: int
    status: int  # 0:waiting, 1:active, 2:closed, 3:bot
    assigned_operator_id: Optional[int]
    created_at: str
    closed_at: Optional[str]
    bot_state: Optional[str] = None  # BOT対応中のみ値を持つ


@dataclass
class Message:
    """チャットメッセージ"""

    id: int
    inquiry_id: int
    sender_type: int  # 0:enduser, 1:operator, 2:system, 3:bot
    sender_name: Optional[str]
    content: str
    created_at: str


@dataclass
class InquiryFirstResponse:
    """問い合わせごとの初回応答集計データ"""

    id: int
    created_at: str
    first_response_at: Optional[str]


# ステータス定数
class OperatorAvailabilityStatus:
    AWAY = 0
    AVAILABLE = 1


class InquiryStatus:
    WAITING = 0
    ACTIVE = 1
    CLOSED = 2
    BOT = 3


class DisplayStatus(str, Enum):
    """オペレータ視点の問い合わせ表示状態"""

    MINE = "mine"
    WAITING = "waiting"
    OTHERS = "others"
    CLOSED = "closed"
    BOT = "bot"


# 表示状態が増減しても並び順を一箇所で変更できるようにする
DISPLAY_STATUS_PRIORITY = (
    DisplayStatus.MINE,
    DisplayStatus.WAITING,
    DisplayStatus.BOT,
    DisplayStatus.OTHERS,
    DisplayStatus.CLOSED,
)


# 送信者タイプ定数
class SenderType:
    ENDUSER = 0
    OPERATOR = 1
    SYSTEM = 2
    BOT = 3


# BOT質問状態定数（inquiries.bot_state に格納する値）
class BotState:
    INQUIRY_CATEGORY = "INQUIRY_CATEGORY"
    SIZE_QUESTION = "SIZE_QUESTION"
    PRICE_RESOLUTION = "PRICE_RESOLUTION"
    ADDITIONAL_QUESTION = "ADDITIONAL_QUESTION"
