"""
WebSocket接続管理: インメモリで接続を管理する
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List

from fastapi import WebSocket


@dataclass
class ConnectionInfo:
    """接続情報"""

    websocket: WebSocket
    user_type: str  # 'enduser' or 'operator'
    last_activity: float = field(default_factory=time.time)


class ConnectionManager:
    """
    WebSocket接続のインメモリ管理
    問い合わせID単位で接続をグループ管理する
    """

    def __init__(self):
        # {inquiry_id: [ConnectionInfo, ...]}
        self._connections: Dict[int, List[ConnectionInfo]] = {}

    async def connect(self, websocket: WebSocket, inquiry_id: int, user_type: str) -> None:
        """接続を登録（WebSocket acceptを含む）"""
        await websocket.accept()
        info = ConnectionInfo(websocket=websocket, user_type=user_type)
        if inquiry_id not in self._connections:
            self._connections[inquiry_id] = []
        self._connections[inquiry_id].append(info)

    def disconnect(self, websocket: WebSocket, inquiry_id: int) -> None:
        """接続を削除"""
        if inquiry_id in self._connections:
            self._connections[inquiry_id] = [
                conn for conn in self._connections[inquiry_id] if conn.websocket != websocket
            ]
            # 空になったらキーを削除
            if not self._connections[inquiry_id]:
                del self._connections[inquiry_id]

    async def broadcast(self, inquiry_id: int, message: dict) -> None:
        """問い合わせグループの全接続にメッセージを送信"""
        if inquiry_id not in self._connections:
            return
        for conn in self._connections[inquiry_id]:
            try:
                await conn.websocket.send_json(message)
            except Exception:
                # 送信失敗した接続は無視（次回のdisconnectで処理される）
                pass

    def update_activity(self, websocket: WebSocket, inquiry_id: int) -> None:
        """最終アクティビティ時刻を更新"""
        if inquiry_id in self._connections:
            for conn in self._connections[inquiry_id]:
                if conn.websocket == websocket:
                    conn.last_activity = time.time()
                    break

    def get_timed_out_inquiries(self, timeout_seconds: int) -> List[int]:
        """タイムアウトした問い合わせIDのリストを返す"""
        now = time.time()
        timed_out = []
        for inquiry_id, connections in self._connections.items():
            # エンドユーザ接続の最終アクティビティをチェック
            enduser_conns = [c for c in connections if c.user_type == "enduser"]
            for conn in enduser_conns:
                if now - conn.last_activity > timeout_seconds:
                    timed_out.append(inquiry_id)
                    break
        return timed_out

    def get_connections(self, inquiry_id: int) -> List[ConnectionInfo]:
        """問い合わせの接続一覧を取得"""
        return self._connections.get(inquiry_id, [])


# シングルトンインスタンス
manager = ConnectionManager()
