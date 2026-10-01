"""
チャットサービス: メッセージ送受信・問い合わせ終了処理
"""

from app.models import InquiryStatus, Message, SenderType
from app.repositories.chat_repository import ChatRepository
from app.repositories.inquiry_repository import InquiryRepository
from app.websocket.connection_manager import manager

# 終了理由ごとのシステムメッセージ
LEAVE_MESSAGE = "ユーザーが退出しました"


class ChatService:
    """チャット関連のビジネスロジック"""

    def __init__(self):
        self.chat_repository = ChatRepository()
        self.inquiry_repository = InquiryRepository()

    async def send_message(
        self,
        inquiry_id: int,
        sender_type: int,
        content: str,
        sender_name: str | None = None,
        operator_id: int | None = None,
    ) -> dict | None:
        """
        メッセージを送信・保存・ブロードキャスト
        権限チェック含む。拒否時はNoneを返す。
        """
        # 問い合わせ取得
        inquiry = self.inquiry_repository.find_by_id(inquiry_id)
        if inquiry is None:
            return None

        # 終了済みチェック
        if inquiry.status == InquiryStatus.CLOSED:
            return None

        # BOT対応中は通常メッセージを受け付けない
        if inquiry.status == InquiryStatus.BOT or inquiry.bot_state is not None:
            return None

        # オペレータの権限チェック
        if sender_type == SenderType.OPERATOR:
            if inquiry.assigned_operator_id != operator_id:
                return None

        # メッセージ保存
        message = self.chat_repository.save_message(
            inquiry_id=inquiry_id,
            sender_type=sender_type,
            sender_name=sender_name,
            content=content,
        )

        message_data = self._to_broadcast_payload(message)
        await manager.broadcast(inquiry_id, message_data)
        return message_data

    async def close_inquiry(self, inquiry_id: int) -> None:
        """
        問い合わせを終了する（タブ閉じ / 明示終了 / タイムアウト共通）
        既に終了済みの場合は何もしない（終了メッセージの重複保存を防ぐ）
        """
        closed = self.inquiry_repository.update_status_closed(inquiry_id)
        if not closed:
            return

        message = self.chat_repository.save_message(
            inquiry_id=inquiry_id,
            sender_type=SenderType.SYSTEM,
            sender_name=None,
            content=LEAVE_MESSAGE,
        )

        await manager.broadcast(inquiry_id, self._to_broadcast_payload(message))
        await manager.broadcast(inquiry_id, {"type": "closed"})

    @staticmethod
    def _to_broadcast_payload(message: Message) -> dict:
        """WebSocket配信用のメッセージデータを組み立てる"""
        return {
            "type": "message",
            "id": message.id,
            "inquiry_id": message.inquiry_id,
            "sender_type": message.sender_type,
            "sender_name": message.sender_name,
            "content": message.content,
            "created_at": message.created_at,
        }
