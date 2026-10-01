"""
認証ルーター: ログイン・ログアウト・自分の情報取得
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.middleware.auth_middleware import get_current_operator
from app.models import Operator
from app.schemas import (
    CurrentOperatorResponse,
    LoginRequest,
    OperatorAvailabilityUpdateRequest,
)
from app.services.auth_service import AuthService
from app.services.operator_service import OperatorService

router = APIRouter()
auth_service = AuthService()
operator_service = OperatorService()


def _to_current_operator_response(operator: Operator) -> CurrentOperatorResponse:
    """認証中オペレータ向けのレスポンスを組み立てる"""
    return CurrentOperatorResponse(
        id=operator.id,
        username=operator.username,
        display_name=operator.display_name,
        availability_status=operator.availability_status,
    )


@router.post("/login", response_model=CurrentOperatorResponse)
def login(body: LoginRequest, response: Response):
    """オペレータログイン"""
    try:
        operator, session_id = auth_service.login(body.username, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # セッションIDをCookieに設定
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
    )

    return _to_current_operator_response(operator)


@router.post("/logout")
def logout(request: Request, response: Response):
    """オペレータログアウト"""
    session_id = request.cookies.get("session_id")
    if session_id:
        auth_service.logout(session_id)

    response.delete_cookie("session_id")
    return {"message": "ログアウトしました"}


@router.get("/me", response_model=CurrentOperatorResponse)
def get_me(operator: Operator = Depends(get_current_operator)):
    """ログイン中のオペレータ情報取得"""
    return _to_current_operator_response(operator)


@router.patch("/me/availability", response_model=CurrentOperatorResponse)
def update_availability(
    body: OperatorAvailabilityUpdateRequest,
    operator: Operator = Depends(get_current_operator),
):
    """ログイン中のオペレータ本人の稼働状態を更新"""
    updated_operator = operator_service.update_availability(operator.id, body.availability_status)
    return _to_current_operator_response(updated_operator)
