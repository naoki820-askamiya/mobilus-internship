# ユニット依存関係

## 依存関係マトリクス

本プロジェクトは単一ユニットのため、ユニット間依存関係はない。
以下はユニット内部のレイヤー間依存関係を示す。

### レイヤー間依存

| 依存元 | 依存先 | 関係 |
|--------|--------|------|
| frontend (React) | backend (FastAPI) | HTTP API + WebSocket |
| routers | services | 直接呼び出し |
| websocket handlers | services | 直接呼び出し |
| services | repositories | 直接呼び出し |
| services | connection_manager | 直接呼び出し |
| BotService | app/bot/questions.py | 質問定義の参照 |
| repositories | database | DB接続 |

---

## 開発順序

単一ユニット内での開発順序（フロントエンド先行）:

```
Phase 1: フロントエンド
  1. プロジェクトセットアップ（Vite + React + TypeScript）
  2. ルーティング・レイアウト構築（AppShell）
  3. エンドユーザチャット画面（モックデータ）
  4. オペレータログイン画面（モック認証）
  5. 問い合わせ一覧画面（モックデータ + 優先順）
  6. 問い合わせ詳細画面（モックデータ）
  7. BOT事前質問UI、待ち時間画面、サマリーボード

Phase 2: バックエンド
  1. プロジェクトセットアップ（FastAPI + SQLite）
  2. データベースモデル・テーブル作成
  3. 認証モジュール（auth）
  4. 問い合わせ管理モジュール（inquiry）
  5. チャットモジュール + WebSocket（chat）
  6. BOT / 待ち時間 / サマリー / 稼働状態
  7. フロントエンドとの結合・モック削除
```

---

## 結合ポイント

フロントエンドとバックエンドの結合は以下のインターフェースで行う:

| インターフェース | エンドポイント | 用途 |
|----------------|--------------|------|
| REST API | `/api/auth/*` | 認証・稼働状態 |
| REST API | `/api/chat/*` | BOT事前質問 |
| REST API | `/api/inquiries/*` | 問い合わせ管理 |
| REST API | `/api/operators/*` | オペレータ管理 |
| REST API | `/api/wait-time/*` | 推定待ち時間 |
| REST API | `/api/summary` | サマリーボード |
| WebSocket | `/ws/chat/enduser/{inquiry_id}` | エンドユーザチャット |
| WebSocket | `/ws/chat/operator/{inquiry_id}` | オペレータチャット |
