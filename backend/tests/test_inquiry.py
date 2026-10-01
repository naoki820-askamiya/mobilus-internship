"""
問い合わせサービスのテスト（リポジトリをモック化、PBT含む）
学生向けサンプル: ビジネスロジックを固定データでテストする方法
"""

import math
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from hypothesis import given, settings
from hypothesis import strategies as st

from app.config import CLOSED_INQUIRY_DISPLAY_LIMIT
from app.models import DisplayStatus, Inquiry, InquiryStatus
from app.services.inquiry_service import InquiryService

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
MOCK_INQUIRIES = [MOCK_INQUIRY_WAITING, MOCK_INQUIRY_ACTIVE, MOCK_INQUIRY_CLOSED]


class TestInquiryServiceAssign:
    """担当割り当てのテスト"""

    @patch("app.services.inquiry_service.InquiryRepository")
    def test_assign_operator_success(self, MockRepo):
        """担当割り当て成功"""
        mock_repo = MockRepo.return_value
        mock_repo.update_assignment.return_value = True
        assigned_inquiry = Inquiry(
            id=1,
            status=InquiryStatus.ACTIVE,
            assigned_operator_id=1,
            created_at="2026-01-01 09:00:00",
            closed_at=None,
        )
        mock_repo.find_by_id.return_value = assigned_inquiry

        service = InquiryService()
        service.repository = mock_repo

        result = service.assign_operator(1, operator_id=1)
        assert result.status == InquiryStatus.ACTIVE
        assert result.assigned_operator_id == 1

    @patch("app.services.inquiry_service.InquiryRepository")
    def test_assign_operator_conflict(self, MockRepo):
        """既に担当がいる場合は409エラー"""
        mock_repo = MockRepo.return_value
        mock_repo.update_assignment.return_value = False  # 排他制御失敗

        service = InquiryService()
        service.repository = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            service.assign_operator(1, operator_id=2)
        assert exc_info.value.status_code == 409


class TestInquiryServiceList:
    """一覧取得のテスト"""

    @patch("app.services.inquiry_service.InquiryRepository")
    def test_list_inquiries_pagination(self, MockRepo):
        """ページネーション情報が正しく計算される"""
        mock_repo = MockRepo.return_value
        mock_repo.find_all.return_value = (MOCK_INQUIRIES, 3)

        service = InquiryService()
        service.repository = mock_repo

        result = service.list_inquiries(page=1, per_page=10, operator_id=1)
        assert result.total == 3
        assert result.total_pages == 1
        assert len(result.items) == 3

    @patch("app.services.inquiry_service.InquiryRepository")
    def test_list_inquiries_display_status(self, MockRepo):
        """表示ステータスが正しく算出される"""
        mock_repo = MockRepo.return_value
        mock_repo.find_all.return_value = (MOCK_INQUIRIES, 3)

        service = InquiryService()
        service.repository = mock_repo

        result = service.list_inquiries(page=1, per_page=10, operator_id=1)
        statuses = [item.display_status for item in result.items]
        assert DisplayStatus.WAITING in statuses
        assert DisplayStatus.MINE in statuses
        assert DisplayStatus.CLOSED in statuses


class TestInquiryServiceSeparatedLists:
    """未完了・完了済みの分離一覧テスト"""

    @patch("app.services.inquiry_service.InquiryRepository")
    def test_open_inquiries_are_sorted_by_operator_priority(self, MockRepo):
        """自分の対応中、未対応、他人の対応中の順で返す"""
        mock_repo = MockRepo.return_value
        mock_repo.find_open.return_value = [
            Inquiry(4, InquiryStatus.ACTIVE, 2, "2026-01-01 08:00:00", None),
            Inquiry(3, InquiryStatus.WAITING, None, "2026-01-01 07:00:00", None),
            Inquiry(2, InquiryStatus.ACTIVE, 1, "2026-01-01 10:00:00", None),
            Inquiry(1, InquiryStatus.ACTIVE, 1, "2026-01-01 09:00:00", None),
        ]
        service = InquiryService()
        service.repository = mock_repo

        result = service.list_open(operator_id=1)

        assert [item.id for item in result] == [1, 2, 3, 4]
        assert [item.display_status for item in result] == [
            DisplayStatus.MINE,
            DisplayStatus.MINE,
            DisplayStatus.WAITING,
            DisplayStatus.OTHERS,
        ]

    @patch("app.services.inquiry_service.InquiryRepository")
    def test_open_priority_changes_with_operator(self, MockRepo):
        """ログイン中のオペレータに応じて自分の対応中が変わる"""
        mock_repo = MockRepo.return_value
        mock_repo.find_open.return_value = [
            Inquiry(1, InquiryStatus.ACTIVE, 1, "2026-01-01 09:00:00", None),
            Inquiry(2, InquiryStatus.ACTIVE, 2, "2026-01-01 10:00:00", None),
        ]
        service = InquiryService()
        service.repository = mock_repo

        result = service.list_open(operator_id=2)

        assert [item.id for item in result] == [2, 1]

    @patch("app.services.inquiry_service.InquiryRepository")
    def test_closed_inquiries_use_configured_limit(self, MockRepo):
        """完了済みは設定された上限件数で取得する"""
        mock_repo = MockRepo.return_value
        mock_repo.find_recent_closed.return_value = [MOCK_INQUIRY_CLOSED]
        service = InquiryService()
        service.repository = mock_repo

        result = service.list_closed()

        mock_repo.find_recent_closed.assert_called_once_with(CLOSED_INQUIRY_DISPLAY_LIMIT)
        assert [item.id for item in result] == [MOCK_INQUIRY_CLOSED.id]
        assert result[0].display_status == DisplayStatus.CLOSED


class TestDisplayStatus:
    """表示ステータス算出のテスト（純粋関数テスト）"""

    def test_waiting(self):
        """WAITING → 'waiting'"""
        result = InquiryService._compute_display_status(MOCK_INQUIRY_WAITING, operator_id=1)
        assert result == DisplayStatus.WAITING

    def test_mine(self):
        """ACTIVE + 自分のID → 'mine'"""
        result = InquiryService._compute_display_status(MOCK_INQUIRY_ACTIVE, operator_id=1)
        assert result == DisplayStatus.MINE

    def test_others(self):
        """ACTIVE + 他人のID → 'others'"""
        result = InquiryService._compute_display_status(MOCK_INQUIRY_ACTIVE, operator_id=99)
        assert result == DisplayStatus.OTHERS

    def test_closed(self):
        """CLOSED → 'closed'"""
        result = InquiryService._compute_display_status(MOCK_INQUIRY_CLOSED, operator_id=1)
        assert result == DisplayStatus.CLOSED

    def test_bot(self):
        """BOT → 'bot'"""
        inquiry = Inquiry(
            id=4,
            status=InquiryStatus.BOT,
            assigned_operator_id=None,
            created_at="2026-01-01 09:00:00",
            closed_at=None,
        )
        result = InquiryService._compute_display_status(inquiry, operator_id=1)
        assert result == DisplayStatus.BOT


class TestDisplayStatusPBT:
    """プロパティベーステスト: 表示ステータス算出"""

    @given(
        status=st.sampled_from(
            [
                InquiryStatus.WAITING,
                InquiryStatus.ACTIVE,
                InquiryStatus.CLOSED,
                InquiryStatus.BOT,
            ]
        ),
        assigned_operator_id=st.one_of(st.none(), st.integers(min_value=1, max_value=100)),
        operator_id=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=200)
    def test_always_returns_valid_status(self, status, assigned_operator_id, operator_id):
        """任意の入力に対して表示ステータスが有効な値のいずれかになる"""
        inquiry = Inquiry(
            id=1,
            status=status,
            assigned_operator_id=assigned_operator_id,
            created_at="",
            closed_at=None,
        )
        result = InquiryService._compute_display_status(inquiry, operator_id)
        assert result in (
            DisplayStatus.WAITING,
            DisplayStatus.MINE,
            DisplayStatus.OTHERS,
            DisplayStatus.CLOSED,
            DisplayStatus.BOT,
        )

    @given(
        total=st.integers(min_value=0, max_value=1000),
        per_page=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=200)
    def test_pagination_calculation(self, total, per_page):
        """ページ数計算が常に正しい"""
        total_pages = math.ceil(total / per_page)
        if total > 0:
            last_page_items = total - (total_pages - 1) * per_page
            assert 1 <= last_page_items <= per_page
        else:
            assert total_pages == 0
