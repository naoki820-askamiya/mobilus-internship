"""
認証サービス: ログイン・ログアウト・セッション検証
"""

from datetime import datetime
from typing import Optional

import bcrypt

from app.database import JST
from app.models import Operator
from app.repositories.auth_repository import AuthRepository


class AuthService:
    """認証関連のビジネスロジック"""

    def __init__(self):
        self.repository = AuthRepository()

    def login(self, username: str, password: str) -> tuple[Operator, str]:
        """
        ログイン処理
        成功時: (Operator, session_id) を返す
        失敗時: ValueError を送出
        """
        # オペレータ検索
        operator = self.repository.find_operator_by_username(username)
        if operator is None:
            raise ValueError("ユーザー名またはパスワードが正しくありません")

        # パスワード検証
        if not bcrypt.checkpw(password.encode(), operator.password_hash.encode()):
            raise ValueError("ユーザー名またはパスワードが正しくありません")

        # セッション作成
        session_id = self.repository.create_session(operator.id)
        return operator, session_id

    def logout(self, session_id: str) -> None:
        """ログアウト処理（セッション削除）"""
        self.repository.delete_session(session_id)

    def get_current_operator(self, session_id: Optional[str]) -> Optional[Operator]:
        """
        セッションIDから現在のオペレータを取得
        無効なセッションの場合はNoneを返す
        """
        if not session_id:
            return None

        session = self.repository.get_session(session_id)
        if session is None:
            return None

        # 有効期限チェック（JSTで比較）
        expires_at = datetime.strptime(session.expires_at, "%Y-%m-%d %H:%M:%S")
        if datetime.now(JST).replace(tzinfo=None) > expires_at:
            # 期限切れセッションを削除
            self.repository.delete_session(session_id)
            return None

        return self.repository.find_operator_by_id(session.operator_id)
