"""
BOTリポジトリ: BOT質問・回答の保存と問い合わせ状態更新

回答保存・次質問保存・状態更新を1トランザクションで行うため、
既存リポジトリとは分けて1接続内でまとめて実行する。
"""

import sqlite3
from typing import Optional, Tuple

from app.database import get_db, now_jst
from app.models import BotState, Inquiry, InquiryStatus, Message, SenderType


def _insert_message(
    conn: sqlite3.Connection,
    inquiry_id: int,
    sender_type: int,
    content: str,
    created_at: str,
) -> Message:
    """メッセージを1件保存して返す"""
    cursor = conn.execute(
        """INSERT INTO messages (inquiry_id, sender_type, sender_name, content, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (inquiry_id, sender_type, None, content, created_at),
    )
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return Message(**dict(row))


class BotRepository:
    """BOT対応中の問い合わせ・メッセージのデータアクセス"""

    def create_bot_inquiry(self, question_text: str) -> Tuple[Inquiry, Message]:
        """BOT対応中の問い合わせを作成し、最初のBOT質問を保存する"""
        with get_db() as conn:
            created_at = now_jst()
            cursor = conn.execute(
                "INSERT INTO inquiries (status, bot_state, created_at) VALUES (?, ?, ?)",
                (InquiryStatus.BOT, BotState.INQUIRY_CATEGORY, created_at),
            )
            inquiry_id = cursor.lastrowid

            question_message = _insert_message(
                conn, inquiry_id, SenderType.BOT, question_text, created_at
            )
            row = conn.execute("SELECT * FROM inquiries WHERE id = ?", (inquiry_id,)).fetchone()
            return Inquiry(**dict(row)), question_message

    def save_answer_and_transition(
        self,
        inquiry_id: int,
        answer_text: str,
        next_status: int,
        next_bot_state: Optional[str],
        bot_message_text: Optional[str],
    ) -> Tuple[Message, Optional[Message]]:
        """
        ユーザ回答の保存、BOT応答の保存、問い合わせ状態の更新を一括で行う
        戻り値: (ユーザ回答メッセージ, BOT応答メッセージ)
        """
        with get_db() as conn:
            created_at = now_jst()

            answer_message = _insert_message(
                conn, inquiry_id, SenderType.ENDUSER, answer_text, created_at
            )

            bot_message = None
            if bot_message_text is not None:
                bot_message = _insert_message(
                    conn, inquiry_id, SenderType.BOT, bot_message_text, created_at
                )

            if next_status == InquiryStatus.CLOSED:
                conn.execute(
                    """UPDATE inquiries
                       SET status = ?, bot_state = ?, closed_at = ?
                       WHERE id = ?""",
                    (next_status, next_bot_state, created_at, inquiry_id),
                )
            else:
                conn.execute(
                    "UPDATE inquiries SET status = ?, bot_state = ? WHERE id = ?",
                    (next_status, next_bot_state, inquiry_id),
                )

            return answer_message, bot_message
