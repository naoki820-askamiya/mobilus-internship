"""
WebSocket ハンドラー: エンドユーザ・オペレータ用のチャット接続

問い合わせはBOT事前質問の開始API側で作成されるため、
WebSocketは作成済みの inquiry_id に対してのみ接続を受け付ける。
BOT対応中の接続は、切断検知とオペレーター対応への切り替え待ちに利用する。
"""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import (
    WS_CODE_FORBIDDEN,
    WS_CODE_INQUIRY_CLOSED,
    WS_CODE_INQUIRY_NOT_FOUND,
    WS_CODE_UNAUTHORIZED,
)
from app.models import InquiryStatus, SenderType
from app.repositories.inquiry_repository import InquiryRepository
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.websocket.connection_manager import manager

router = APIRouter()
chat_service = ChatService()
auth_service = AuthService()
inquiry_repository = InquiryRepository()


@router.websocket("/ws/chat/enduser/{inquiry_id}")
async def enduser_chat(websocket: WebSocket, inquiry_id: int):
    """エンドユーザ用WebSocketエンドポイント"""
    inquiry = inquiry_repository.find_by_id(inquiry_id)

    if inquiry is None:
        await websocket.close(code=WS_CODE_INQUIRY_NOT_FOUND, reason="問い合わせが見つかりません")
        return

    if inquiry.status == InquiryStatus.CLOSED:
        await websocket.close(code=WS_CODE_INQUIRY_CLOSED, reason="この問い合わせは終了しています")
        return

    await manager.connect(websocket, inquiry_id, "enduser")
    await websocket.send_json({"type": "connected", "inquiry_id": inquiry_id})

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            if payload.get("type") == "message":
                content = payload.get("content", "").strip()
                if not content:
                    continue

                # BOT対応中は send_message 側で拒否される
                await chat_service.send_message(
                    inquiry_id=inquiry_id,
                    sender_type=SenderType.ENDUSER,
                    content=content,
                )
                manager.update_activity(websocket, inquiry_id)

            elif payload.get("type") == "close":
                # 明示的な終了
                await chat_service.close_inquiry(inquiry_id)
                break

    except WebSocketDisconnect:
        # タブ閉じによる切断 → 終了処理（終了済みの場合は何もしない）
        await chat_service.close_inquiry(inquiry_id)
    finally:
        manager.disconnect(websocket, inquiry_id)


@router.websocket("/ws/chat/operator/{inquiry_id}")
async def operator_chat(websocket: WebSocket, inquiry_id: int):
    """
    オペレータ用WebSocketエンドポイント
    認証と担当確認を行ってから接続する
    """
    # Cookieからセッション検証
    session_id = websocket.cookies.get("session_id")
    operator = auth_service.get_current_operator(session_id)

    if operator is None:
        await websocket.close(code=WS_CODE_UNAUTHORIZED, reason="認証が必要です")
        return

    inquiry = inquiry_repository.find_by_id(inquiry_id)
    if inquiry is None:
        await websocket.close(code=WS_CODE_INQUIRY_NOT_FOUND, reason="問い合わせが見つかりません")
        return

    if inquiry.assigned_operator_id != operator.id:
        await websocket.close(code=WS_CODE_FORBIDDEN, reason="この問い合わせの担当ではありません")
        return

    # 接続登録
    await manager.connect(websocket, inquiry_id, "operator")

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            if payload.get("type") == "message":
                content = payload.get("content", "").strip()
                if content:
                    await chat_service.send_message(
                        inquiry_id=inquiry_id,
                        sender_type=SenderType.OPERATOR,
                        content=content,
                        sender_name=operator.display_name,
                        operator_id=operator.id,
                    )

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, inquiry_id)
