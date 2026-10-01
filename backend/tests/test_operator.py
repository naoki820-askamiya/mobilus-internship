"""
オペレータ管理サービスのテスト（リポジトリをモック化）
学生向けサンプル: パスワード自動生成やバリデーションのテスト方法
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models import Operator, OperatorAvailabilityStatus
from app.repositories.operator_repository import OperatorRepository
from app.services.operator_service import OperatorService

# テスト用の固定データ
MOCK_OPERATOR_ADMIN = Operator(
    id=1,
    username="admin",
    password_hash="hashed",
    display_name="管理者",
    availability_status=OperatorAvailabilityStatus.AWAY,
    created_at="2026-01-01 09:00:00",
)
MOCK_OPERATOR_NEW = Operator(
    id=2,
    username="newuser",
    password_hash="hashed",
    display_name="新規ユーザー",
    availability_status=OperatorAvailabilityStatus.AWAY,
    created_at="2026-01-01 10:00:00",
)


class TestOperatorServiceCreate:
    """オペレータ追加のテスト"""

    @patch("app.services.operator_service.bcrypt")
    @patch("app.services.operator_service.OperatorRepository")
    def test_create_operator_success(self, MockRepo, mock_bcrypt):
        """オペレータ追加が成功し、パスワードが12文字英数字で自動生成される"""
        mock_repo = MockRepo.return_value
        mock_repo.find_by_username.return_value = None  # 重複なし
        mock_repo.create.return_value = MOCK_OPERATOR_NEW
        mock_bcrypt.hashpw.return_value = b"hashed"
        mock_bcrypt.gensalt.return_value = b"salt"

        service = OperatorService()
        service.repository = mock_repo

        operator, password = service.create_operator("newuser", "新規ユーザー")

        assert operator.username == "newuser"
        assert len(password) == 12
        assert password.isalnum()
        mock_repo.find_by_username.assert_called_once_with("newuser")
        mock_repo.create.assert_called_once()

    @patch("app.services.operator_service.OperatorRepository")
    def test_create_operator_duplicate_username(self, MockRepo):
        """既存のusernameと重複する場合は409エラー"""
        mock_repo = MockRepo.return_value
        mock_repo.find_by_username.return_value = MOCK_OPERATOR_ADMIN  # 重複あり

        service = OperatorService()
        service.repository = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            service.create_operator("admin", "重複テスト")
        assert exc_info.value.status_code == 409


class TestOperatorServiceDelete:
    """オペレータ削除のテスト"""

    @patch("app.services.operator_service.OperatorRepository")
    def test_delete_operator_success(self, MockRepo):
        """他のオペレータを削除できる"""
        mock_repo = MockRepo.return_value

        service = OperatorService()
        service.repository = mock_repo

        service.delete_operator(target_id=2, current_operator_id=1)
        mock_repo.delete.assert_called_once_with(2)

    @patch("app.services.operator_service.OperatorRepository")
    def test_delete_self_forbidden(self, MockRepo):
        """自分自身は削除できない（403）"""
        service = OperatorService()

        with pytest.raises(HTTPException) as exc_info:
            service.delete_operator(target_id=1, current_operator_id=1)
        assert exc_info.value.status_code == 403


class TestOperatorAvailability:
    """オペレータ稼働状態更新のテスト"""

    @patch("app.services.operator_service.OperatorRepository")
    def test_update_availability_delegates_to_repository(self, MockRepo):
        """認証済みIDと検証済み状態をリポジトリへ渡す"""
        mock_repo = MockRepo.return_value
        mock_repo.update_availability.return_value = MOCK_OPERATOR_NEW
        service = OperatorService()
        service.repository = mock_repo

        result = service.update_availability(
            MOCK_OPERATOR_NEW.id,
            OperatorAvailabilityStatus.AWAY,
        )

        assert result == MOCK_OPERATOR_NEW
        mock_repo.update_availability.assert_called_once_with(
            MOCK_OPERATOR_NEW.id,
            OperatorAvailabilityStatus.AWAY,
        )

    @patch("app.repositories.operator_repository.get_db")
    def test_update_availability_returns_updated_operator(self, mock_get_db):
        """状態更新と更新後の取得を同じDB接続で行う"""
        connection = MagicMock()
        select_cursor = MagicMock()
        select_cursor.fetchone.return_value = {
            "id": MOCK_OPERATOR_ADMIN.id,
            "username": MOCK_OPERATOR_ADMIN.username,
            "password_hash": MOCK_OPERATOR_ADMIN.password_hash,
            "display_name": MOCK_OPERATOR_ADMIN.display_name,
            "availability_status": OperatorAvailabilityStatus.AVAILABLE,
            "created_at": MOCK_OPERATOR_ADMIN.created_at,
        }
        connection.execute.side_effect = [MagicMock(), select_cursor]
        mock_get_db.return_value.__enter__.return_value = connection

        result = OperatorRepository().update_availability(
            MOCK_OPERATOR_ADMIN.id,
            OperatorAvailabilityStatus.AVAILABLE,
        )

        assert result.availability_status == OperatorAvailabilityStatus.AVAILABLE
        update_query, update_parameters = connection.execute.call_args_list[0].args
        assert "UPDATE operators SET availability_status = ?" in update_query
        assert update_parameters == (
            OperatorAvailabilityStatus.AVAILABLE,
            MOCK_OPERATOR_ADMIN.id,
        )


class TestOperatorServiceList:
    """オペレータ一覧のテスト"""

    @patch("app.services.operator_service.OperatorRepository")
    def test_list_operators(self, MockRepo):
        """一覧取得でリポジトリのfind_allが呼ばれる"""
        mock_repo = MockRepo.return_value
        mock_repo.find_all.return_value = [MOCK_OPERATOR_ADMIN, MOCK_OPERATOR_NEW]

        service = OperatorService()
        service.repository = mock_repo

        operators = service.list_operators()
        assert len(operators) == 2
        assert operators[0].username == "admin"
        mock_repo.find_all.assert_called_once()
