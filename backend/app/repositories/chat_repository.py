"""
チャットリポジトリ: メッセージの保存・取得
"""

from typing import List

from app.database import get_db, now_jst
from app.models import Message


class ChatRepository:
    """チャットメッセージのデータアクセス"""

    def save_message(
        self, inquiry_id: int, sender_type: int, sender_name: str | None, content: str
    ) -> Message:
        """メッセージを保存"""
        with get_db() as conn:
            cursor = conn.execute(
                """INSERT INTO messages (inquiry_id, sender_type, sender_name, content, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (inquiry_id, sender_type, sender_name, content, now_jst()),
            )
            message_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
            return Message(**dict(row))

    def find_by_inquiry_id(self, inquiry_id: int) -> List[Message]:
        """問い合わせIDに紐づくメッセージを取得"""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE inquiry_id = ? ORDER BY created_at ASC",
                (inquiry_id,),
            ).fetchall()
            return [Message(**dict(row)) for row in rows]
