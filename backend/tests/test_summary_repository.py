"""サマリーリポジトリの取得条件テスト"""

from datetime import date

from app import config
from app.database import get_db, init_db
from app.models import InquiryStatus, SenderType
from app.repositories.summary_repository import SummaryRepository


def test_find_inquiries_with_first_response_filters_date_and_sender(
    monkeypatch, tmp_path
):
    """指定日だけを対象に最初のオペレータ応答を取得する"""
    database_path = tmp_path / "summary_repository.db"
    monkeypatch.setattr(config, "DB_PATH", str(database_path))
    init_db()

    with get_db() as conn:
        conn.execute(
            "INSERT INTO inquiries (status, created_at) VALUES (?, ?)",
            (InquiryStatus.CLOSED, "2026-08-17 23:59:59"),
        )
        responded_inquiry_id = conn.execute(
            "INSERT INTO inquiries (status, created_at) VALUES (?, ?)",
            (InquiryStatus.CLOSED, "2026-08-18 00:00:00"),
        ).lastrowid
        unanswered_inquiry_id = conn.execute(
            "INSERT INTO inquiries (status, created_at) VALUES (?, ?)",
            (InquiryStatus.WAITING, "2026-08-18 23:59:59"),
        ).lastrowid
        conn.execute(
            "INSERT INTO inquiries (status, created_at) VALUES (?, ?)",
            (InquiryStatus.WAITING, "2026-08-19 00:00:00"),
        )

        messages = [
            (responded_inquiry_id, SenderType.ENDUSER, "質問", "2026-08-18 00:00:00"),
            (responded_inquiry_id, SenderType.SYSTEM, "接続", "2026-08-18 00:00:30"),
            (responded_inquiry_id, SenderType.OPERATOR, "後の返信", "2026-08-18 00:03:00"),
            (responded_inquiry_id, SenderType.OPERATOR, "最初の返信", "2026-08-18 00:02:00"),
        ]
        conn.executemany(
            """INSERT INTO messages
               (inquiry_id, sender_type, content, created_at)
               VALUES (?, ?, ?, ?)""",
            messages,
        )

    inquiries = SummaryRepository().find_inquiries_with_first_response(
        date(2026, 8, 18)
    )

    assert [inquiry.id for inquiry in inquiries] == [
        responded_inquiry_id,
        unanswered_inquiry_id,
    ]
    assert inquiries[0].first_response_at == "2026-08-18 00:02:00"
    assert inquiries[1].first_response_at is None
