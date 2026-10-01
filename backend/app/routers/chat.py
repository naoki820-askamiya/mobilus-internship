"""
チャットルーター: BOT事前質問の開始・回答
"""

from app.models import Message
from app.schemas import (
    BotAnswerRequest,
    BotOptionResponse,
    BotQuestionResponse,
    BotStepResponse,
    MessageResponse,
)
from app.services.bot_service import BotService, BotStepResult
from fastapi import APIRouter

router = APIRouter()
bot_service = BotService()


def _to_message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        inquiry_id=message.inquiry_id,
        sender_type=message.sender_type,
        sender_name=message.sender_name,
        content=message.content,
        created_at=message.created_at,
    )


def _to_step_response(step: BotStepResult) -> BotStepResponse:
    question = None
    if step.question is not None and step.question_message is not None:
        question = BotQuestionResponse(
            message_id=step.question_message.id,
            state=step.question.state,
            type=step.question.question_type,
            text=step.question.text,
            options=[
                BotOptionResponse(value=option.value, label=option.label)
                for option in step.question.options
            ],
        )

    return BotStepResponse(
        inquiry_id=step.inquiry_id,
        result=step.result,
        messages=[_to_message_response(message) for message in step.messages],
        question=question,
    )


@router.post("/start", response_model=BotStepResponse, status_code=201)
def start_bot_chat():
    """BOT事前質問を開始する（問い合わせを作成し、最初の質問を返す）"""
    return _to_step_response(bot_service.start())


@router.post("/{inquiry_id}/bot/answer", response_model=BotStepResponse)
async def answer_bot_question(inquiry_id: int, request: BotAnswerRequest):
    """BOT質問へ回答し、次の質問・オペレーター対応・終了のいずれかを返す"""
    step = await bot_service.answer(inquiry_id, request.state, request.answer)
    return _to_step_response(step)
