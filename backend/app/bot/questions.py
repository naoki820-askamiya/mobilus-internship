"""
BOT質問定義: 質問文・質問形式・選択肢・料金計算ルール

質問定義はDBに保存せず、本モジュールを唯一の定義元とする。
DBへ保存するのは「実際に表示した質問文」と「ユーザの回答内容」のみ。
"""

from dataclasses import dataclass, replace
from typing import Dict, Tuple

from app.models import BotState


class QuestionType:
    """フロントエンドが表示するUIの種類"""

    CHOICE = "CHOICE"
    SIZE = "SIZE"


class AnswerValue:
    """選択式回答の値"""

    PRICE = "PRICE"
    OTHER = "OTHER"
    UNKNOWN_MEASUREMENT = "UNKNOWN_MEASUREMENT"
    UNRELATED = "UNRELATED"
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    HAS_MORE = "HAS_MORE"
    NO_MORE = "NO_MORE"


@dataclass(frozen=True)
class BotOption:
    """選択肢"""

    value: str
    label: str


@dataclass(frozen=True)
class BotQuestion:
    """BOTが提示する質問"""

    state: str
    question_type: str
    text: str
    options: Tuple[BotOption, ...]


# === サイズ入力の制約 ===

SIZE_MIN_CM = 1
SIZE_MAX_CM = 1000

# === 料金計算ルール（三辺合計の上限cm, 料金円）===

PRICE_TIERS: Tuple[Tuple[int, int], ...] = (
    (150, 250),
    (200, 500),
    (250, 1000),
)
PRICE_OVER_HIGHEST_TIER = 1500

# === メッセージテンプレート ===

SIZE_ANSWER_TEMPLATE = "縦{length_cm}cm、横{width_cm}cm、高さ{height_cm}cm"
PRICE_RESOLUTION_TEMPLATE = (
    "三辺の合計は{total_cm}cmです。\n料金の目安は{price}円です。\n解決しましたか？"
)
OPERATOR_HANDOFF_MESSAGE = "オペレーターにおつなぎします。少々お待ちください。"
COMPLETED_MESSAGE = "解決してよかったです。お問い合わせありがとうございました。"


QUESTIONS: Dict[str, BotQuestion] = {
    BotState.INQUIRY_CATEGORY: BotQuestion(
        state=BotState.INQUIRY_CATEGORY,
        question_type=QuestionType.CHOICE,
        text="お問い合わせ内容を選択してください。",
        options=(
            BotOption(AnswerValue.PRICE, "料金"),
            BotOption(AnswerValue.OTHER, "その他"),
        ),
    ),
    BotState.SIZE_QUESTION: BotQuestion(
        state=BotState.SIZE_QUESTION,
        question_type=QuestionType.SIZE,
        text="料金の目安を計算します。ごみの三辺（縦・横・高さ）をcmで入力してください。",
        options=(
            BotOption(AnswerValue.UNKNOWN_MEASUREMENT, "サイズの測り方がわからない"),
            BotOption(AnswerValue.UNRELATED, "サイズに関係ない質問です"),
        ),
    ),
    # textは料金計算結果に応じて差し替えるため、ここではテンプレートを保持する
    BotState.PRICE_RESOLUTION: BotQuestion(
        state=BotState.PRICE_RESOLUTION,
        question_type=QuestionType.CHOICE,
        text=PRICE_RESOLUTION_TEMPLATE,
        options=(
            BotOption(AnswerValue.RESOLVED, "はい"),
            BotOption(AnswerValue.UNRESOLVED, "いいえ"),
        ),
    ),
    BotState.ADDITIONAL_QUESTION: BotQuestion(
        state=BotState.ADDITIONAL_QUESTION,
        question_type=QuestionType.CHOICE,
        text="他に質問はありますか？",
        options=(
            BotOption(AnswerValue.HAS_MORE, "はい"),
            BotOption(AnswerValue.NO_MORE, "いいえ"),
        ),
    ),
}


def calculate_price(total_cm: int) -> int:
    """三辺合計から料金を算出する"""
    for max_total_cm, price in PRICE_TIERS:
        if total_cm <= max_total_cm:
            return price
    return PRICE_OVER_HIGHEST_TIER


def build_price_resolution_question(total_cm: int, price: int) -> BotQuestion:
    """料金計算結果を埋め込んだ解決確認の質問を生成する"""
    base = QUESTIONS[BotState.PRICE_RESOLUTION]
    return replace(base, text=PRICE_RESOLUTION_TEMPLATE.format(total_cm=total_cm, price=price))


def find_option_label(question: BotQuestion, value: str) -> str | None:
    """選択肢の値に対応する表示文言を返す（未定義の値はNone）"""
    for option in question.options:
        if option.value == value:
            return option.label
    return None
