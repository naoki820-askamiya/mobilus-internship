"""
チャットサービスのテスト（リポジトリをモック化）
学生向けサンプル: asyncテストとモックの組み合わせ
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.models import Inquiry, InquiryStatus, Message, SenderType
from app.services.chat_service import ChatService

# テスト用の固定データ
MOCK_INQUIRY_WAITING = Inquiry(
    id=1,
    status=InquiryStatus.WAITING,
    assigned_operator_id=None,
    created_at="2026-01-01 09:00:00",
    closed_at=None,
)
MOCK_INQUIRY_ACTIVE = Inquiry(
    id=2,
    status=InquiryStatus.ACTIVE,
    assigned_operator_id=1,
    created_at="2026-01-01 09:05:00",
    closed_at=None,
)
MOCK_INQUIRY_CLOSED = Inquiry(
    id=3,
    status=InquiryStatus.CLOSED,
    assigned_operator_id=1,
    created_at="2026-01-01 08:00:00",
    closed_at="2026-01-01 08:30:00",
)
MOCK_MESSAGE = Message(
    id=1,
    inquiry_id=1,
    sender_type=SenderType.ENDUSER,
    sender_name=None,
    content="テストメッセージ",
    created_at="2026-01-01 09:00:30",
)


class TestChatServiceSendMessage:
    """メッセージ送信のテスト"""

    @pytest.mark.asyncio
    @patch("app.services.chat_service.manager")
    @patch("app.services.chat_service.ChatRepository")
    @patch("app.services.chat_service.InquiryRepository")
    async def test_enduser_can_send_to_waiting(self, MockInqRepo, MockChatRepo, mock_manager):
        """エンドユーザはWAITING状態の問い合わせに送信可能"""
        mock_inq_repo = MockInqRepo.return_value
        mock_inq_repo.find_by_id.return_value = MOCK_INQUIRY_WAITING

        mock_chat_repo = MockChatRepo.return_value
        mock_chat_repo.save_message.return_value = MOCK_MESSAGE

        mock_manager.broadcast = AsyncMock()

        service = ChatService()
        service.inquiry_repository = mock_inq_repo
        service.chat_repository = mock_chat_repo

        result = await service.send_message(
            inquiry_id=1,
            sender_type=SenderType.ENDUSER,
            content="テストメッセージ",
        )
        assert result is not None
        assert result["content"] == "テストメッセージ"
        mock_chat_repo.save_message.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.chat_service.manager")
    @patch("app.services.chat_service.ChatRepository")
    @patch("app.services.chat_service.InquiryRepository")
    async def test_operator_cannot_send_without_assignment(
        self, MockInqRepo, MockChatRepo, mock_manager
    ):
        """オペレータは担当していない問い合わせに送信不可"""
        mock_inq_repo = MockInqRepo.return_value
        mock_inq_repo.find_by_id.return_value = MOCK_INQUIRY_WAITING  # 担当者なし

        service = ChatService()
        service.inquiry_repository = mock_inq_repo

        result = await service.send_message(
            inquiry_id=1,
            sender_type=SenderType.OPERATOR,
            content="テスト",
            operator_id=1,
        )
        assert result is None  # 送信拒否

    @pytest.mark.asyncio
    @patch("app.services.chat_service.manager")
    @patch("app.services.chat_service.ChatRepository")
    @patch("app.services.chat_service.InquiryRepository")
    async def test_operator_can_send_when_assigned(self, MockInqRepo, MockChatRepo, mock_manager):
        """オペレータは自分の担当する問い合わせに送信可能"""
        mock_inq_repo = MockInqRepo.return_value
        mock_inq_repo.find_by_id.return_value = MOCK_INQUIRY_ACTIVE  # operator_id=1が担当

        mock_chat_repo = MockChatRepo.return_value
        mock_chat_repo.save_message.return_value = MOCK_MESSAGE

        mock_manager.broadcast = AsyncMock()

        service = ChatService()
        service.inquiry_repository = mock_inq_repo
        service.chat_repository = mock_chat_repo

        result = await service.send_message(
            inquiry_id=2,
            sender_type=SenderType.OPERATOR,
            content="対応します",
            sender_name="管理者",
            operator_id=1,
        )
        assert result is not None
        mock_chat_repo.save_message.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.chat_service.manager")
    @patch("app.services.chat_service.ChatRepository")
    @patch("app.services.chat_service.InquiryRepository")
    async def test_cannot_send_to_closed(self, MockInqRepo, MockChatRepo, mock_manager):
        """終了した問い合わせには送信不可"""
        mock_inq_repo = MockInqRepo.return_value
        mock_inq_repo.find_by_id.return_value = MOCK_INQUIRY_CLOSED

        service = ChatService()
        service.inquiry_repository = mock_inq_repo

        result = await service.send_message(
            inquiry_id=3,
            sender_type=SenderType.ENDUSER,
            content="まだいますか？",
        )
        assert result is None


class TestChatServiceCloseInquiry:
    """問い合わせ終了のテスト"""

    @pytest.mark.asyncio
    @patch("app.services.chat_service.manager")
    @patch("app.services.chat_service.ChatRepository")
    @patch("app.services.chat_service.InquiryRepository")
    async def test_close_inquiry(self, MockInqRepo, MockChatRepo, mock_manager):
        """終了処理でステータス更新とシステムメッセージ保存が行われる"""
        mock_inq_repo = MockInqRepo.return_value
        mock_chat_repo = MockChatRepo.return_value

        system_msg = Message(
            id=99,
            inquiry_id=1,
            sender_type=SenderType.SYSTEM,
            sender_name=None,
            content="ユーザーが退出しました",
            created_at="2026-01-01 09:30:00",
        )
        mock_chat_repo.save_message.return_value = system_msg
        mock_manager.broadcast = AsyncMock()

        service = ChatService()
        service.inquiry_repository = mock_inq_repo
        service.chat_repository = mock_chat_repo

        await service.close_inquiry(1)

        # ステータス更新が呼ばれたか
        mock_inq_repo.update_status_closed.assert_called_once_with(1)
        # システムメッセージが保存されたか
        mock_chat_repo.save_message.assert_called_once()
        # ブロードキャストが2回呼ばれたか（メッセージ通知 + closed通知）
        assert mock_manager.broadcast.call_count == 2
