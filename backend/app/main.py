"""
FastAPI アプリケーション エントリポイント
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.database import init_db
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.inquiry import router as inquiry_router
from app.routers.operator import router as operator_router
from app.routers.summary import router as summary_router
from app.routers.wait_time import router as wait_time_router
from app.websocket.chat_ws import router as chat_ws_router

# FastAPIアプリケーション作成
app = FastAPI(title="チャットサービス API", version="1.0.0")

# CORS設定（フロントエンドからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(auth_router, prefix="/api/auth", tags=["認証"])
app.include_router(chat_router, prefix="/api/chat", tags=["BOT事前質問"])
app.include_router(inquiry_router, prefix="/api/inquiries", tags=["問い合わせ"])
app.include_router(operator_router, prefix="/api/operators", tags=["オペレータ管理"])
app.include_router(summary_router, prefix="/api/summary", tags=["サマリーボード"])
app.include_router(wait_time_router, prefix="/api/wait-time", tags=["待ち時間"])
app.include_router(chat_ws_router, tags=["チャット WebSocket"])


@app.on_event("startup")
def startup():
    """アプリケーション起動時にDBを初期化"""
    init_db()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
