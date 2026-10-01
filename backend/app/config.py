"""
アプリケーション設定値
変更が必要な場合はここを修正する
"""

import os
from typing import Dict

# データベースファイルパス
DB_PATH = os.getenv("DB_PATH", "chat_service.db")

# セッション有効期限（秒）: 8時間
SESSION_EXPIRY_SECONDS = 8 * 60 * 60

# ページング設定
DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 100
CLOSED_INQUIRY_DISPLAY_LIMIT = 50

# タイムアウト設定
TIMEOUT_SECONDS = 30 * 60  # 30分
TIMEOUT_CHECK_INTERVAL_SECONDS = 60  # 60秒間隔でチェック

# 待ち時間推定設定
ESTIMATED_MINUTES_PER_INQUIRY = 5
CONCURRENT_INQUIRIES_PER_OPERATOR = 2
HOURLY_WAIT_TIME_START_HOUR = 8
HOURLY_WAIT_TIME_END_HOUR = 18
HOURLY_WAIT_TIME_MINUTES_BY_HOUR: Dict[int, int] = {
    8: 2,
    9: 8,
    10: 12,
    11: 15,
    12: 10,
    13: 5,
    14: 4,
    15: 6,
    16: 12,
    17: 9,
    18: 3,
}

# パスワード自動生成設定
GENERATED_PASSWORD_LENGTH = 12

# CORS設定
CORS_ORIGINS = ["http://localhost:3000"]

# WebSocket クローズコード（アプリケーション定義: 4000番台）
WS_CODE_UNAUTHORIZED = 4001
WS_CODE_FORBIDDEN = 4003
WS_CODE_INQUIRY_NOT_FOUND = 4004
WS_CODE_INQUIRY_CLOSED = 4005
