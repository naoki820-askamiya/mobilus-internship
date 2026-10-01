"""
問い合わせリポジトリ: 問い合わせのCRUD操作
"""

from typing import List, Optional, Tuple

from app.database import get_db, now_jst
from app.models import Inquiry, InquiryStatus, Message


class InquiryRepository:
    """問い合わせ関連のデータアクセス"""

    def find_open(self) -> List[Inquiry]:
        """未完了の問い合わせを全件取得"""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM inquiries WHERE status != ? ORDER BY created_at ASC, id ASC",
                (InquiryStatus.CLOSED,),
            ).fetchall()
            return [Inquiry(**dict(row)) for row in rows]

    def find_recent_closed(self, limit: int) -> List[Inquiry]:
        """完了済みの問い合わせを完了日時の新しい順で取得"""
        with get_db() as conn:
            rows = conn.execute(
                """SELECT * FROM inquiries
                   WHERE status = ?
                   ORDER BY closed_at DESC, id DESC
                   LIMIT ?""",
                (InquiryStatus.CLOSED, limit),
            ).fetchall()
            return [Inquiry(**dict(row)) for row in rows]

    def find_all(self, page: int, per_page: int) -> Tuple[List[Inquiry], int]:
        """ページング付きで全件取得（ID降順）"""
        with get_db() as conn:
            # 総件数取得
            total = conn.execute("SELECT COUNT(*) FROM inquiries").fetchone()[0]

            # ページング付きデータ取得（ID降順）
            offset = (page - 1) * per_page
            rows = conn.execute(
                "SELECT * FROM inquiries ORDER BY id DESC LIMIT ? OFFSET ?",
                (per_page, offset),
            ).fetchall()

            inquiries = [Inquiry(**dict(row)) for row in rows]
            return inquiries, total

    def find_by_id(self, inquiry_id: int) -> Optional[Inquiry]:
        """IDで問い合わせを検索"""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM inquiries WHERE id = ?", (inquiry_id,)).fetchone()
            if row is None:
                return None
            return Inquiry(**dict(row))

    def update_assignment(self, inquiry_id: int, operator_id: int) -> bool:
        """
        担当者を更新（排他制御付き）
        成功時: True, 失敗時（既に担当あり）: False
        """
        with get_db() as conn:
            cursor = conn.execute(
                """UPDATE inquiries
                   SET assigned_operator_id = ?, status = ?
                   WHERE id = ? AND assigned_operator_id IS NULL AND status = ?""",
                (operator_id, InquiryStatus.ACTIVE, inquiry_id, InquiryStatus.WAITING),
            )
            return cursor.rowcount > 0

    def update_status_closed(self, inquiry_id: int) -> bool:
        """
        問い合わせを終了状態に更新（BOT状態も解除する）
        既に終了済みの場合は False を返す
        """
        with get_db() as conn:
            cursor = conn.execute(
                """UPDATE inquiries
                   SET status = ?, bot_state = NULL, closed_at = ?
                   WHERE id = ? AND status != ?""",
                (InquiryStatus.CLOSED, now_jst(), inquiry_id, InquiryStatus.CLOSED),
            )
            return cursor.rowcount > 0

    def find_messages_by_inquiry_id(self, inquiry_id: int) -> List[Message]:
        """問い合わせIDに紐づくメッセージを全件取得（保存順）"""
        with get_db() as conn:
            # created_at は秒精度のため、同時刻のメッセージが前後しないよう id 順で取得する
            rows = conn.execute(
                "SELECT * FROM messages WHERE inquiry_id = ? ORDER BY id ASC",
                (inquiry_id,),
            ).fetchall()
            return [Message(**dict(row)) for row in rows]

    def count_waiting(self) -> int:
        """待機中かつ未割り当ての問い合わせ件数を取得"""
        with get_db() as conn:
            return conn.execute(
                """SELECT COUNT(*) FROM inquiries
                   WHERE status = ? AND assigned_operator_id IS NULL""",
                (InquiryStatus.WAITING,),
            ).fetchone()[0]

    def count_active(self) -> int:
        """対応中の問い合わせ件数を取得"""
        with get_db() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM inquiries WHERE status = ?",
                (InquiryStatus.ACTIVE,),
            ).fetchone()[0]
