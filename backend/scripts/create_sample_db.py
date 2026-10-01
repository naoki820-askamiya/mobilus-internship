"""
サマリーボードのE2E確認用に、再現可能な1週間分のサンプルDBを作成する。

BOT事前質問から始まる現在の問い合わせフローをそのまま再現し、
BOTだけで解決した問い合わせと、オペレーターへ引き継がれた問い合わせの両方を生成する。

実行例:
    python -m scripts.create_sample_db --force
"""

import argparse
import os
import random
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import bcrypt

from app import config
from app.bot import questions
from app.bot.questions import AnswerValue
from app.config import CONCURRENT_INQUIRIES_PER_OPERATOR
from app.database import get_db, init_db
from app.models import (
    BotState,
    InquiryStatus,
    OperatorAvailabilityStatus,
    SenderType,
)

DEFAULT_DATABASE_PATH = "sample_chat_service.db"
DEFAULT_START_DATE = date(2026, 8, 1)
DEFAULT_RANDOM_SEED = 20260801
AVERAGE_DAILY_SESSIONS = 225
# 月曜から日曜までの利用者数の増減。週末を少なく、金曜を多くする。
WEEKDAY_SESSION_OFFSETS = (30, 0, 15, -15, 50, -30, -50)
BUSINESS_START_HOUR = 9
LUNCH_START_HOUR = 12
LUNCH_END_HOUR = 13
SECOND_PEAK_START_HOUR = 16
BUSINESS_END_HOUR = 17
# 10時と16時を頂点にし、9時を11時より少し多くする
HOURLY_SESSION_WEIGHTS = (15, 20, 14, 7, 5, 5, 13, 21)
HOURLY_WEIGHT_VARIATION_RATIO = 0.03
SECONDS_PER_HOUR = 60 * 60
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_PASSWORD = "password123"

# 平均が5分になり、3〜10分の範囲に収まる固定分布
HANDLING_DURATION_MINUTES = (
    3,
    3,
    3,
    4,
    4,
    4,
    4,
    4,
    5,
    5,
    5,
    5,
    5,
    5,
    6,
    6,
    6,
    6,
    7,
    10,
)

# BOT事前質問だけで解決し、オペレーターへ引き継がれない問い合わせの割合
BOT_RESOLUTION_RATIO = 0.3
# ユーザーがBOTの質問に回答するまでの所要時間（秒）
BOT_ANSWER_MIN_SECONDS = 10
BOT_ANSWER_MAX_SECONDS = 60
# 料金計算の三辺に使用する代表的なサイズ（cm）。料金区分が偏らない範囲を選ぶ
SAMPLE_SIDE_LENGTHS_CM = (20, 30, 40, 50, 60, 80, 100, 120)

USER_QUESTIONS = (
    "商品の使い方を教えてください",
    "契約内容を確認したいです",
    "ログインできなくなりました",
    "登録情報を変更したいです",
    "料金について質問があります",
    "解約方法を教えてください",
)

OPERATOR_RESPONSES = (
    "お問い合わせありがとうございます。確認いたします。",
    "ご不便をおかけして申し訳ありません。状況を確認します。",
    "承知しました。必要な手続きをご案内します。",
    "お問い合わせ内容を確認しました。順番にご説明します。",
)

USER_CLOSING_MESSAGE = "ありがとうございます"
SYSTEM_EXIT_MESSAGE = "ユーザーが退出しました"


class BotScenario:
    """BOT事前質問の会話パターン"""

    OTHER_CATEGORY = "OTHER_CATEGORY"
    UNKNOWN_SIZE = "UNKNOWN_SIZE"
    PRICE_UNRESOLVED = "PRICE_UNRESOLVED"
    PRICE_RESOLVED = "PRICE_RESOLVED"


# オペレーターへ引き継がれる会話パターンと、その出現比率
HANDOFF_SCENARIOS = (
    BotScenario.OTHER_CATEGORY,
    BotScenario.UNKNOWN_SIZE,
    BotScenario.PRICE_UNRESOLVED,
)
HANDOFF_SCENARIO_WEIGHTS = (5, 2, 3)


@dataclass
class GeneratedMessage:
    """DBへ保存するメッセージ1件分のデータ"""

    sender_type: int
    sender_name: Optional[str]
    content: str
    created_at: datetime


@dataclass
class GeneratedSession:
    """DBへ保存する問い合わせ1件分のデータ"""

    created_at: datetime
    closed_at: datetime
    messages: List[GeneratedMessage]
    # BOTだけで解決した問い合わせはオペレーターが介在しないためNoneになる
    operator_id: Optional[int] = None
    first_response_at: Optional[datetime] = None


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description="E2E確認用の1週間分のサンプルDBを作成します"
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_DATABASE_PATH,
        help=f"出力先DB（デフォルト: {DEFAULT_DATABASE_PATH}）",
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=DEFAULT_START_DATE,
        help="生成開始日 YYYY-MM-DD（デフォルト: 2026-08-01）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_RANDOM_SEED,
        help=f"乱数seed（デフォルト: {DEFAULT_RANDOM_SEED}）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="出力先DBが存在する場合に置き換える",
    )
    return parser.parse_args()


def allocate_hourly_session_counts(
    session_count: int,
    random_generator: random.Random,
) -> List[int]:
    """基本の山型を維持しつつ、時間帯ごとの件数に小さな揺らぎを加える"""
    varied_weights = [
        weight
        * random_generator.uniform(
            1 - HOURLY_WEIGHT_VARIATION_RATIO,
            1 + HOURLY_WEIGHT_VARIATION_RATIO,
        )
        for weight in HOURLY_SESSION_WEIGHTS
    ]
    total_weight = sum(varied_weights)
    exact_counts = [
        session_count * weight / total_weight for weight in varied_weights
    ]
    counts = [int(exact_count) for exact_count in exact_counts]
    remaining_count = session_count - sum(counts)
    remainder_order = sorted(
        range(len(exact_counts)),
        key=lambda index: exact_counts[index] - counts[index],
        reverse=True,
    )
    for index in remainder_order[:remaining_count]:
        counts[index] += 1
    return counts


def generate_datetimes_in_hour(
    target_date: date,
    hour: int,
    count: int,
    random_generator: random.Random,
) -> List[datetime]:
    """グラフの形を保ちながら、1時間内の問い合わせ時刻をランダム化"""
    generated_datetimes: List[datetime] = []

    for index in range(count):
        segment_start = index * SECONDS_PER_HOUR // count
        segment_end = (index + 1) * SECONDS_PER_HOUR // count
        selected_offset = random_generator.randrange(
            segment_start, max(segment_start + 1, segment_end)
        )
        generated_datetimes.append(
            datetime.combine(target_date, time(hour))
            + timedelta(seconds=selected_offset)
        )
    return generated_datetimes


def generate_arrival_times(
    target_date: date,
    session_count: int,
    random_generator: random.Random,
) -> List[datetime]:
    """10時と16時を頂点とする滑らかな時間帯分布を生成"""
    hourly_counts = allocate_hourly_session_counts(
        session_count, random_generator
    )
    arrival_times = [
        arrival_at
        for hour_offset, hourly_count in enumerate(hourly_counts)
        for arrival_at in generate_datetimes_in_hour(
            target_date,
            BUSINESS_START_HOUR + hour_offset,
            hourly_count,
            random_generator,
        )
    ]
    return sorted(arrival_times)


def choose_bot_scenario(random_generator: random.Random) -> str:
    """BOT完結とオペレーター引き継ぎの比率に従って会話パターンを決める"""
    if random_generator.random() < BOT_RESOLUTION_RATIO:
        return BotScenario.PRICE_RESOLVED
    return random_generator.choices(
        HANDOFF_SCENARIOS, weights=HANDOFF_SCENARIO_WEIGHTS
    )[0]


def find_option_label(state: str, value: str) -> str:
    """BOT質問定義から選択肢の表示文言を取得"""
    label = questions.find_option_label(questions.QUESTIONS[state], value)
    if label is None:
        raise ValueError(f"選択肢が定義されていません: {state} / {value}")
    return label


def append_bot_turn(
    messages: List[GeneratedMessage],
    answered_at: datetime,
    answer_text: str,
    bot_message_text: str,
) -> None:
    """ユーザー回答とBOT応答を追加する

    BotRepository は回答とBOT応答を同一トランザクションで保存するため、
    実データと同じく両者を同じ時刻で記録する。
    """
    messages.append(
        GeneratedMessage(SenderType.ENDUSER, None, answer_text, answered_at)
    )
    messages.append(
        GeneratedMessage(SenderType.BOT, None, bot_message_text, answered_at)
    )


def next_answer_time(
    current_at: datetime, random_generator: random.Random
) -> datetime:
    """ユーザーが質問を読んで回答するまでの時間を進める"""
    return current_at + timedelta(
        seconds=random_generator.randint(
            BOT_ANSWER_MIN_SECONDS, BOT_ANSWER_MAX_SECONDS
        )
    )


def generate_bot_conversation(
    arrival_at: datetime,
    scenario: str,
    random_generator: random.Random,
) -> Tuple[List[GeneratedMessage], datetime]:
    """BotService の状態遷移どおりにBOT事前質問の会話を生成

    戻り値は (メッセージ一覧, BOT対応が終わった時刻)。
    """
    messages = [
        GeneratedMessage(
            SenderType.BOT,
            None,
            questions.QUESTIONS[BotState.INQUIRY_CATEGORY].text,
            arrival_at,
        )
    ]
    answered_at = arrival_at

    if scenario == BotScenario.OTHER_CATEGORY:
        answered_at = next_answer_time(answered_at, random_generator)
        append_bot_turn(
            messages,
            answered_at,
            find_option_label(BotState.INQUIRY_CATEGORY, AnswerValue.OTHER),
            questions.OPERATOR_HANDOFF_MESSAGE,
        )
        return messages, answered_at

    answered_at = next_answer_time(answered_at, random_generator)
    append_bot_turn(
        messages,
        answered_at,
        find_option_label(BotState.INQUIRY_CATEGORY, AnswerValue.PRICE),
        questions.QUESTIONS[BotState.SIZE_QUESTION].text,
    )

    if scenario == BotScenario.UNKNOWN_SIZE:
        answered_at = next_answer_time(answered_at, random_generator)
        append_bot_turn(
            messages,
            answered_at,
            find_option_label(
                BotState.SIZE_QUESTION, AnswerValue.UNKNOWN_MEASUREMENT
            ),
            questions.OPERATOR_HANDOFF_MESSAGE,
        )
        return messages, answered_at

    length_cm, width_cm, height_cm = (
        random_generator.choice(SAMPLE_SIDE_LENGTHS_CM) for _ in range(3)
    )
    total_cm = length_cm + width_cm + height_cm
    price_question = questions.build_price_resolution_question(
        total_cm, questions.calculate_price(total_cm)
    )
    answered_at = next_answer_time(answered_at, random_generator)
    append_bot_turn(
        messages,
        answered_at,
        questions.SIZE_ANSWER_TEMPLATE.format(
            length_cm=length_cm, width_cm=width_cm, height_cm=height_cm
        ),
        price_question.text,
    )

    if scenario == BotScenario.PRICE_UNRESOLVED:
        answered_at = next_answer_time(answered_at, random_generator)
        append_bot_turn(
            messages,
            answered_at,
            find_option_label(
                BotState.PRICE_RESOLUTION, AnswerValue.UNRESOLVED
            ),
            questions.OPERATOR_HANDOFF_MESSAGE,
        )
        return messages, answered_at

    answered_at = next_answer_time(answered_at, random_generator)
    append_bot_turn(
        messages,
        answered_at,
        find_option_label(BotState.PRICE_RESOLUTION, AnswerValue.RESOLVED),
        questions.QUESTIONS[BotState.ADDITIONAL_QUESTION].text,
    )
    answered_at = next_answer_time(answered_at, random_generator)
    append_bot_turn(
        messages,
        answered_at,
        find_option_label(BotState.ADDITIONAL_QUESTION, AnswerValue.NO_MORE),
        questions.COMPLETED_MESSAGE,
    )
    return messages, answered_at


def generate_operator_messages(
    handoff_at: datetime,
    first_response_at: datetime,
    closed_at: datetime,
    operator_name: str,
    random_generator: random.Random,
) -> List[GeneratedMessage]:
    """引き継ぎ後の、ユーザーの質問から退出までのメッセージを生成"""
    middle_message_at = (
        first_response_at + (closed_at - first_response_at) / 2
    )
    return [
        # 引き継ぎ直後にユーザーが用件を送るため、初回応答より前の時刻に置く
        GeneratedMessage(
            SenderType.ENDUSER,
            None,
            random_generator.choice(USER_QUESTIONS),
            handoff_at,
        ),
        GeneratedMessage(
            SenderType.OPERATOR,
            operator_name,
            random_generator.choice(OPERATOR_RESPONSES),
            first_response_at,
        ),
        GeneratedMessage(
            SenderType.ENDUSER, None, USER_CLOSING_MESSAGE, middle_message_at
        ),
        GeneratedMessage(
            SenderType.SYSTEM, None, SYSTEM_EXIT_MESSAGE, closed_at
        ),
    ]


def get_available_start(
    handoff_at: datetime,
    available_at: datetime,
    duration: timedelta,
    operator_takes_lunch: bool,
) -> datetime:
    """オペレーターの空き時刻と昼休みを考慮して対応開始時刻を算出"""
    start_at = max(handoff_at, available_at)
    if not operator_takes_lunch:
        return start_at

    lunch_start = datetime.combine(handoff_at.date(), time(LUNCH_START_HOUR))
    lunch_end = datetime.combine(handoff_at.date(), time(LUNCH_END_HOUR))
    overlaps_lunch = start_at < lunch_start and start_at + duration > lunch_start
    starts_during_lunch = lunch_start <= start_at < lunch_end
    if overlaps_lunch or starts_during_lunch:
        return lunch_end
    return start_at


def generate_daily_sessions(
    target_date: date,
    session_count: int,
    operator_names: Dict[int, str],
    random_generator: random.Random,
) -> List[GeneratedSession]:
    """BOT事前質問・2名体制・昼休みを考慮して1日分の完了済みセッションを生成"""
    arrival_times = generate_arrival_times(
        target_date, session_count, random_generator
    )
    operator_ids = sorted(operator_names)
    operator_available_slots = {
        operator_id: [
            datetime.combine(target_date, time(BUSINESS_START_HOUR))
            for _ in range(CONCURRENT_INQUIRIES_PER_OPERATOR)
        ]
        for operator_id in operator_ids
    }
    sessions: List[GeneratedSession] = []

    for arrival_at in arrival_times:
        scenario = choose_bot_scenario(random_generator)
        messages, bot_ended_at = generate_bot_conversation(
            arrival_at, scenario, random_generator
        )

        if scenario == BotScenario.PRICE_RESOLVED:
            sessions.append(
                GeneratedSession(
                    created_at=arrival_at,
                    closed_at=bot_ended_at,
                    messages=messages,
                )
            )
            continue

        duration = timedelta(
            minutes=random_generator.choice(HANDLING_DURATION_MINUTES)
        )
        # オペレーターの待ち行列に入るのはBOTから引き継がれた時点
        start_candidates = [
            (
                get_available_start(
                    handoff_at=bot_ended_at,
                    available_at=available_at,
                    duration=duration,
                    operator_takes_lunch=operator_id == operator_ids[1],
                ),
                operator_id,
                slot_index,
            )
            for operator_id in operator_ids
            for slot_index, available_at in enumerate(
                operator_available_slots[operator_id]
            )
        ]
        first_response_at, operator_id, slot_index = min(start_candidates)
        closed_at = first_response_at + duration
        operator_available_slots[operator_id][slot_index] = closed_at
        messages.extend(
            generate_operator_messages(
                handoff_at=bot_ended_at,
                first_response_at=first_response_at,
                closed_at=closed_at,
                operator_name=operator_names[operator_id],
                random_generator=random_generator,
            )
        )
        sessions.append(
            GeneratedSession(
                created_at=arrival_at,
                closed_at=closed_at,
                messages=messages,
                operator_id=operator_id,
                first_response_at=first_response_at,
            )
        )

    return sessions


def generate_daily_session_counts(
    start_date: date,
) -> List[int]:
    """曜日傾向を反映し、週平均225件・±50件の利用者数を生成"""
    return [
        AVERAGE_DAILY_SESSIONS
        + WEEKDAY_SESSION_OFFSETS[
            (start_date + timedelta(days=day_offset)).weekday()
        ]
        for day_offset in range(len(WEEKDAY_SESSION_OFFSETS))
    ]


def create_operators(start_date: date) -> Dict[int, str]:
    """ログイン可能な2名のオペレーターを作成

    availability_status のDBデフォルトは離席(0)であり、そのままでは
    待ち時間APIが稼働中オペレーター数を0と判定するため、稼働可能で作成する。
    """
    created_at = datetime.combine(start_date, time(BUSINESS_START_HOUR))
    password_hash = bcrypt.hashpw(
        DEFAULT_PASSWORD.encode(), bcrypt.gensalt()
    ).decode()

    with get_db() as conn:
        conn.execute(
            """UPDATE operators
               SET display_name = ?, availability_status = ?, created_at = ?
               WHERE username = ?""",
            (
                "オペレーターA",
                OperatorAvailabilityStatus.AVAILABLE,
                created_at.strftime(TIMESTAMP_FORMAT),
                "admin",
            ),
        )
        conn.execute(
            """INSERT INTO operators
               (username, password_hash, display_name, availability_status, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                "operator2",
                password_hash,
                "オペレーターB",
                OperatorAvailabilityStatus.AVAILABLE,
                created_at.strftime(TIMESTAMP_FORMAT),
            ),
        )
        rows = conn.execute(
            """SELECT id, display_name
               FROM operators
               WHERE username IN (?, ?)
               ORDER BY id ASC""",
            ("admin", "operator2"),
        ).fetchall()
        return {row["id"]: row["display_name"] for row in rows}


def save_sessions(sessions: List[GeneratedSession]) -> None:
    """生成したセッションとメッセージを1トランザクションで保存"""
    with get_db() as conn:
        for session in sessions:
            inquiry_id = conn.execute(
                """INSERT INTO inquiries
                   (status, assigned_operator_id, created_at, closed_at, bot_state)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    InquiryStatus.CLOSED,
                    session.operator_id,
                    session.created_at.strftime(TIMESTAMP_FORMAT),
                    session.closed_at.strftime(TIMESTAMP_FORMAT),
                    # 完了済みの問い合わせはBOT質問状態を保持しない
                    None,
                ),
            ).lastrowid
            conn.executemany(
                """INSERT INTO messages
                   (inquiry_id, sender_type, sender_name, content, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (
                        inquiry_id,
                        message.sender_type,
                        message.sender_name,
                        message.content,
                        message.created_at.strftime(TIMESTAMP_FORMAT),
                    )
                    for message in session.messages
                ],
            )


def remove_database_files(database_path: Path) -> None:
    """DB本体とSQLiteのサイドカーファイルを削除"""
    for suffix in ("", "-wal", "-shm"):
        path = Path(f"{database_path}{suffix}")
        if path.exists():
            path.unlink()


def finalize_database(database_path: Path) -> None:
    """一つのDBファイルだけで配布可能な状態に統合"""
    with sqlite3.connect(database_path) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("PRAGMA journal_mode=DELETE")


def main() -> None:
    """サンプルDBを再現可能な固定条件で作成"""
    args = parse_args()
    output_path = Path(args.database).expanduser().resolve()
    temporary_path = output_path.with_name(f".{output_path.name}.tmp")

    if output_path.exists() and not args.force:
        raise SystemExit(
            f"{output_path} は既に存在します。置き換える場合は --force を指定してください。"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    remove_database_files(temporary_path)
    config.DB_PATH = str(temporary_path)
    init_db()

    operator_names = create_operators(args.start_date)
    random_generator = random.Random(args.seed)
    daily_session_counts = generate_daily_session_counts(args.start_date)
    all_sessions: List[GeneratedSession] = []
    daily_counts: List[Tuple[date, int]] = []

    for day_offset, session_count in enumerate(daily_session_counts):
        target_date = args.start_date + timedelta(days=day_offset)
        sessions = generate_daily_sessions(
            target_date, session_count, operator_names, random_generator
        )
        all_sessions.extend(sessions)
        daily_counts.append((target_date, len(sessions)))

    save_sessions(all_sessions)
    finalize_database(temporary_path)
    remove_database_files(output_path)
    os.replace(temporary_path, output_path)

    operator_sessions = [
        session
        for session in all_sessions
        if session.first_response_at is not None
    ]
    bot_resolved_count = len(all_sessions) - len(operator_sessions)
    average_handling_minutes = sum(
        (session.closed_at - session.first_response_at).total_seconds() / 60
        for session in operator_sessions
    ) / len(operator_sessions)
    peak_count = sum(
        1
        for session in all_sessions
        if BUSINESS_START_HOUR <= session.created_at.hour < LUNCH_START_HOUR
        or SECOND_PEAK_START_HOUR
        <= session.created_at.hour
        < BUSINESS_END_HOUR
    )
    peak_ratio = peak_count / len(all_sessions)
    latest_closed_at = max(session.closed_at for session in all_sessions)

    print("\nサンプルDBを作成しました")
    print(f"出力先: {output_path}")
    for target_date, count in daily_counts:
        print(f"  {target_date.isoformat()}: {count}セッション")
    print(f"合計: {len(all_sessions)}セッション")
    print(f"ピーク時間比率: {peak_ratio:.1%}")
    print(
        f"BOT完結: {bot_resolved_count}セッション "
        f"({bot_resolved_count / len(all_sessions):.1%})"
    )
    print(f"オペレーター対応: {len(operator_sessions)}セッション")
    print(f"平均対応時間: {average_handling_minutes:.1f}分")
    print(f"最終完了日時: {latest_closed_at.strftime(TIMESTAMP_FORMAT)}")
    print("\nログイン情報")
    print(f"  admin / {DEFAULT_PASSWORD}")
    print(f"  operator2 / {DEFAULT_PASSWORD}")
    print("\n起動方法")
    print(f'DB_PATH="{output_path}" python -m app.main')


if __name__ == "__main__":
    main()
