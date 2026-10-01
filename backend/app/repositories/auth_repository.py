"""
認証リポジトリ: オペレータ検索・セッション管理
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from app.config import SESSION_EXPIRY_SECONDS
from app.database import JST, get_db
from app.models import Operator, OperatorAvailabilityStatus, Session


class AuthRepository:
    """認証関連のデータアクセス"""

    def find_operator_by_username(self, username: str) -> Optional[Operator]:
        """ユーザー名でオペレータを検索"""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM operators WHERE username = ?", (username,)).fetchone()
            if row is None:
                return None
            return Operator(**dict(row))

    def create_session(self, operator_id: int) -> str:
        """セッションを作成し、session_idを返す"""
        session_id = str(uuid.uuid4())
        now = datetime.now(JST)
        expires_at = now + timedelta(seconds=SESSION_EXPIRY_SECONDS)

        with get_db() as conn:
            conn.execute(
                "INSERT INTO sessions (id, operator_id, created_at, expires_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    session_id,
                    operator_id,
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                    expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
        return session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """セッションを取得"""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                return None
            return Session(**dict(row))

    def delete_session(self, session_id: str) -> None:
        """セッションを削除"""
        with get_db() as conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    def find_operator_by_id(self, operator_id: int) -> Optional[Operator]:
        """IDでオペレータを検索"""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM operators WHERE id = ?", (operator_id,)).fetchone()
            if row is None:
                return None
            return Operator(**dict(row))

    def count_active_operators(self, updated_at: str) -> int:
        """指定時刻に稼働中かつ有効なセッションを持つオペレータ数を取得"""
        with get_db() as conn:
            return conn.execute(
                """SELECT COUNT(DISTINCT sessions.operator_id)
                   FROM sessions
                   INNER JOIN operators
                       ON operators.id = sessions.operator_id
                   WHERE sessions.expires_at > ?
                     AND operators.availability_status = ?""",
                (updated_at, OperatorAvailabilityStatus.AVAILABLE),
            ).fetchone()[0]
