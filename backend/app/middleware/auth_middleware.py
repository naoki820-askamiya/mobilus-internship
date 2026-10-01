"""
認証ミドルウェア: リクエストからセッションを検証しオペレータを取得する
"""

from fastapi import HTTPException, Request

from app.models import Operator
from app.services.auth_service import AuthService

auth_service = AuthService()


def get_current_operator(request: Request) -> Operator:
    """
    リクエストのCookieからセッションを検証し、オペレータを返す
    未認証の場合は 401 HTTPException を送出
    """
    session_id = request.cookies.get("session_id")
    operator = auth_service.get_current_operator(session_id)

    if operator is None:
        raise HTTPException(status_code=401, detail="認証が必要です")

    return operator
