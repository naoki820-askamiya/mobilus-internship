"""
オペレータサービス: オペレータの追加・削除・一覧取得
"""

import secrets
import string

import bcrypt
from fastapi import HTTPException

from app.config import GENERATED_PASSWORD_LENGTH
from app.models import Operator
from app.repositories.operator_repository import OperatorRepository


class OperatorService:
    """オペレータ管理のビジネスロジック"""

    def __init__(self):
        self.repository = OperatorRepository()

    def list_operators(self) -> list[Operator]:
        """全オペレータを取得"""
        return self.repository.find_all()

    def create_operator(self, username: str, display_name: str) -> tuple[Operator, str]:
        """
        オペレータを作成しパスワードを自動発行
        戻り値: (Operator, 生成されたパスワード平文)
        """
        # username重複チェック
        existing = self.repository.find_by_username(username)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="このユーザー名は既に使用されています",
            )

        # パスワード自動生成（英数字12文字）
        alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(alphabet) for _ in range(GENERATED_PASSWORD_LENGTH))

        # パスワードハッシュ化
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # DB保存
        operator = self.repository.create(username, password_hash, display_name)

        return operator, password

    def update_availability(self, operator_id: int, availability_status: int) -> Operator:
        """オペレータ本人の稼働状態を更新する"""
        return self.repository.update_availability(operator_id, availability_status)

    def delete_operator(self, target_id: int, current_operator_id: int) -> None:
        """
        オペレータを削除
        自分自身の削除は禁止
        """
        if target_id == current_operator_id:
            raise HTTPException(
                status_code=403,
                detail="自分自身を削除することはできません",
            )

        self.repository.delete(target_id)
