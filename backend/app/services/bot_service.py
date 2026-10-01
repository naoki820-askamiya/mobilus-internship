"""
BOTサービス: 事前質問の開始・回答受付・状態遷移・料金計算
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from fastapi import HTTPException

from app.bot import questions
from app.bot.questions import AnswerValue, BotQuestion, QuestionType
from app.models import BotState, InquiryStatus, Message
from app.repositories.bot_repository import BotRepository
from app.repositories.inquiry_repository import InquiryRepository
from app.schemas import BotAnswerPayload
from app.websocket.connection_manager import manager


class BotResult:
    """BOT処理の結果種別"""

    QUESTION = "QUESTION"
    OPERATOR = "OPERATOR"
    COMPLETED = "COMPLETED"


@dataclass
class BotStepResult:
    """BOT処理1ステップの結果"""

    inquiry_id: int
    result: str
    messages: List[Message]
    question: Optional[BotQuestion] = None
    question_message: Optional[Message] = None


@dataclass
class _Transition:
    """回答に対する遷移先"""

    result: str
    next_status: int
    next_bot_state: Optional[str]
    bot_message_text: Optional[str]
    question: Optional[BotQuestion] = None


class BotService:
    """BOT事前質問のビジネスロジック"""

    def __init__(self):
        self.bot_repository = BotRepository()
        self.inquiry_repository = InquiryRepository()

    def start(self) -> BotStepResult:
        """BOT対応の問い合わせを作成し、最初の質問を返す"""
        question = questions.QUESTIONS[BotState.INQUIRY_CATEGORY]
        inquiry, question_message = self.bot_repository.create_bot_inquiry(question.text)

        return BotStepResult(
            inquiry_id=inquiry.id,
            result=BotResult.QUESTION,
            messages=[question_message],
            question=question,
            question_message=question_message,
        )

    async def answer(self, inquiry_id: int, state: str, payload: BotAnswerPayload) -> BotStepResult:
        """回答を保存し、次の質問・オペレーター対応・終了のいずれかへ遷移する"""
        inquiry = self.inquiry_repository.find_by_id(inquiry_id)
        if inquiry is None:
            raise HTTPException(status_code=404, detail="問い合わせが見つかりません")

        if inquiry.status != InquiryStatus.BOT or inquiry.bot_state is None:
            raise HTTPException(status_code=409, detail="この問い合わせはBOT対応中ではありません")

        # 古い画面からの回答や二重送信を防ぐため、DBの状態を正として照合する
        if inquiry.bot_state != state:
            raise HTTPException(status_code=409, detail="質問の状態が最新ではありません")

        answer_text, transition = self._resolve_transition(inquiry.bot_state, payload)

        answer_message, bot_message = self.bot_repository.save_answer_and_transition(
            inquiry_id=inquiry_id,
            answer_text=answer_text,
            next_status=transition.next_status,
            next_bot_state=transition.next_bot_state,
            bot_message_text=transition.bot_message_text,
        )

        messages = [answer_message]
        if bot_message is not None:
            messages.append(bot_message)

        if transition.result == BotResult.COMPLETED:
            await manager.broadcast(inquiry_id, {"type": "closed"})

        return BotStepResult(
            inquiry_id=inquiry_id,
            result=transition.result,
            messages=messages,
            question=transition.question,
            question_message=bot_message if transition.question is not None else None,
        )

    def _resolve_transition(
        self, state: str, payload: BotAnswerPayload
    ) -> Tuple[str, _Transition]:
        """現在状態と回答から、保存する回答文言と遷移先を決定する"""
        if state == BotState.INQUIRY_CATEGORY:
            value, label = self._read_choice(state, payload)
            if value == AnswerValue.PRICE:
                return label, self._to_question(BotState.SIZE_QUESTION)
            return label, self._to_operator()

        if state == BotState.SIZE_QUESTION:
            if payload.type == QuestionType.SIZE:
                return self._resolve_size_answer(payload)
            _, label = self._read_choice(state, payload)
            return label, self._to_operator()

        if state == BotState.PRICE_RESOLUTION:
            value, label = self._read_choice(state, payload)
            if value == AnswerValue.RESOLVED:
                return label, self._to_question(BotState.ADDITIONAL_QUESTION)
            return label, self._to_operator()

        if state == BotState.ADDITIONAL_QUESTION:
            value, label = self._read_choice(state, payload)
            if value == AnswerValue.HAS_MORE:
                return label, self._to_question(BotState.INQUIRY_CATEGORY)
            return label, self._to_completed()

        raise HTTPException(status_code=409, detail="不正な質問状態です")

    def _read_choice(self, state: str, payload: BotAnswerPayload) -> Tuple[str, str]:
        """選択式の回答を検証し、(値, 表示文言) を返す"""
        if payload.type != QuestionType.CHOICE or payload.value is None:
            raise HTTPException(status_code=422, detail="選択式の回答が必要です")

        label = questions.find_option_label(questions.QUESTIONS[state], payload.value)
        if label is None:
            raise HTTPException(status_code=422, detail="選択肢に存在しない回答です")
        return payload.value, label

    def _resolve_size_answer(self, payload: BotAnswerPayload) -> Tuple[str, _Transition]:
        """サイズ入力を検証し、料金計算結果の質問へ遷移する"""
        sides = (payload.length_cm, payload.width_cm, payload.height_cm)
        if any(side is None for side in sides):
            raise HTTPException(status_code=422, detail="縦・横・高さをすべて入力してください")

        if any(
            side < questions.SIZE_MIN_CM or side > questions.SIZE_MAX_CM for side in sides
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"各辺は{questions.SIZE_MIN_CM}cm以上"
                    f"{questions.SIZE_MAX_CM}cm以下で入力してください"
                ),
            )

        total_cm = sum(sides)
        price = questions.calculate_price(total_cm)
        question = questions.build_price_resolution_question(total_cm, price)

        answer_text = questions.SIZE_ANSWER_TEMPLATE.format(
            length_cm=payload.length_cm,
            width_cm=payload.width_cm,
            height_cm=payload.height_cm,
        )
        transition = _Transition(
            result=BotResult.QUESTION,
            next_status=InquiryStatus.BOT,
            next_bot_state=question.state,
            bot_message_text=question.text,
            question=question,
        )
        return answer_text, transition

    @staticmethod
    def _to_question(next_state: str) -> _Transition:
        question = questions.QUESTIONS[next_state]
        return _Transition(
            result=BotResult.QUESTION,
            next_status=InquiryStatus.BOT,
            next_bot_state=next_state,
            bot_message_text=question.text,
            question=question,
        )

    @staticmethod
    def _to_operator() -> _Transition:
        return _Transition(
            result=BotResult.OPERATOR,
            next_status=InquiryStatus.WAITING,
            next_bot_state=None,
            bot_message_text=questions.OPERATOR_HANDOFF_MESSAGE,
        )

    @staticmethod
    def _to_completed() -> _Transition:
        return _Transition(
            result=BotResult.COMPLETED,
            next_status=InquiryStatus.CLOSED,
            next_bot_state=None,
            bot_message_text=questions.COMPLETED_MESSAGE,
        )
