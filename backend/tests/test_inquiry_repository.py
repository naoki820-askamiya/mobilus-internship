"""問い合わせリポジトリの取得条件テスト"""

from app import config
from app.database import get_db, init_db
from app.models import InquiryStatus
from app.repositories.inquiry_repository import InquiryRepository


def test_find_recent_closed_limits_and_orders_results(monkeypatch, tmp_path):
    """完了済みはDB側で指定件数に制限し、同一完了日時ならID降順にする"""
    database_path = tmp_path / "inquiry_repository.db"
    monkeypatch.setattr(config, "DB_PATH", str(database_path))
    init_db()

    timestamp = "2026-01-01 10:00:00"
    with get_db() as conn:
        for _ in range(51):
            conn.execute(
                """INSERT INTO inquiries
                   (status, assigned_operator_id, created_at, closed_at)
                   VALUES (?, NULL, ?, ?)""",
                (InquiryStatus.CLOSED, timestamp, timestamp),
            )

    inquiries = InquiryRepository().find_recent_closed(limit=50)

    assert len(inquiries) == 50
    assert inquiries[0].id == 51
    assert inquiries[-1].id == 2
