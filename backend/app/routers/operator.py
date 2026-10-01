"""
オペレータ管理ルーター: 一覧取得・追加・削除
"""

from typing import List

from fastapi import APIRouter, Depends, Response

from app.middleware.auth_middleware import get_current_operator
from app.models import Operator
from app.schemas import OperatorCreateRequest, OperatorCreateResponse, OperatorResponse
from app.services.operator_service import OperatorService

router = APIRouter()
operator_service = OperatorService()


@router.get("", response_model=List[OperatorResponse])
def list_operators(_operator: Operator = Depends(get_current_operator)):
    """オペレータ一覧取得"""
    operators = operator_service.list_operators()
    return [
        OperatorResponse(id=op.id, username=op.username, display_name=op.display_name)
        for op in operators
    ]


@router.post("", response_model=OperatorCreateResponse, status_code=201)
def create_operator(
    body: OperatorCreateRequest,
    _operator: Operator = Depends(get_current_operator),
):
    """オペレータ追加（パスワード自動発行）"""
    operator, generated_password = operator_service.create_operator(
        body.username, body.display_name
    )
    return OperatorCreateResponse(
        operator=OperatorResponse(
            id=operator.id,
            username=operator.username,
            display_name=operator.display_name,
        ),
        generated_password=generated_password,
    )


@router.delete("/{operator_id}", status_code=204)
def delete_operator(
    operator_id: int,
    current_operator: Operator = Depends(get_current_operator),
):
    """オペレータ削除"""
    operator_service.delete_operator(operator_id, current_operator.id)
    return Response(status_code=204)
