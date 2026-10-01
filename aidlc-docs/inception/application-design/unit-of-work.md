# ユニット定義

## ユニット構成

本プロジェクトは**単一ユニット**として開発する。フロントエンド（React）とバックエンド（FastAPI）を1つのユニットにまとめ、一括で設計・実装を行う。

---

## Unit-001: チャットサービス（chat-service）

| 項目 | 内容 |
|------|------|
| ユニット名 | chat-service |
| タイプ | フルスタックアプリケーション（モノリス） |
| 責務 | エンドユーザ/オペレータ向けチャットサービスの全機能 |
| 開発順序 | フロントエンド先行（UI → バックエンド） |

### 含まれるコンポーネント

**フロントエンド:**
- FE-001: EndUserInquiry
- FE-002: OperatorLogin
- FE-003: InquiryList
- FE-004: InquiryDetail
- FE-005: AppShell
- FE-006: OperatorAdd
- FE-007: OperatorList
- FE-008: （EndUserInquiry に統合）
- FE-009: SummaryBoard

**バックエンド:**
- BE-001: auth
- BE-002: inquiry
- BE-003: chat
- BE-004: connection_manager
- BE-005: database
- BE-006: operator
- BE-007: bot
- BE-008: wait_time
- BE-009: summary

---

## 開発順序（フロントエンド先行）

### Phase 1: フロントエンド実装
- UI・画面遷移を先に実装
- モックデータで動作確認
- 画面レイアウト・コンポーネント構成の確定

### Phase 2: バックエンド実装
- REST API エンドポイントの実装
- WebSocket ハンドラーの実装
- SQLite データベース・リポジトリの実装
- フロントエンドとの結合

---

## コード構成戦略（Greenfield）

```text
/
├── frontend/                    # React (TypeScript) フロントエンド
│   ├── public/
│   ├── src/
│   │   ├── components/          # 共通UIコンポーネント
│   │   │   ├── AssignButton.tsx
│   │   │   ├── BotQuestionInput.tsx
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── ChoiceQuestion.tsx
│   │   │   ├── ConnectionStatus.tsx
│   │   │   ├── EndButton.tsx
│   │   │   ├── HourlyResponseTimeChart.tsx
│   │   │   ├── HourlySessionChart.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   ├── OperatorNav.tsx
│   │   │   ├── Pagination.tsx
│   │   │   ├── ProtectedRoute.tsx
│   │   │   ├── SizeQuestion.tsx
│   │   │   ├── StatusBadge.tsx
│   │   │   └── WaitTimeChart.tsx
│   │   ├── pages/
│   │   │   ├── EndUserInquiry.tsx
│   │   │   ├── InquiryDetail.tsx
│   │   │   ├── InquiryList.tsx
│   │   │   ├── OperatorAdd.tsx
│   │   │   ├── OperatorList.tsx
│   │   │   ├── OperatorLogin.tsx
│   │   │   ├── SummaryBoard.tsx
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx
│   │   ├── hooks/
│   │   │   ├── useBotChat.ts
│   │   │   └── useChat.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── utils/
│   │   │   └── formatDuration.ts
│   │   ├── constants.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/                     # Python FastAPI バックエンド
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI アプリエントリポイント
│   │   ├── config.py            # 設定値管理
│   │   ├── database.py          # DB接続・テーブル作成・簡易マイグレーション
│   │   ├── models.py            # dataclass モデル定義
│   │   ├── schemas.py           # Pydantic スキーマ
│   │   ├── bot/                 # BOT質問定義
│   │   │   ├── __init__.py
│   │   │   └── questions.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   ├── inquiry.py
│   │   │   ├── operator.py
│   │   │   ├── summary.py
│   │   │   └── wait_time.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── bot_service.py
│   │   │   ├── chat_service.py
│   │   │   ├── inquiry_service.py
│   │   │   ├── operator_service.py
│   │   │   ├── summary_service.py
│   │   │   └── wait_time_service.py
│   │   ├── repositories/
│   │   │   ├── auth_repository.py
│   │   │   ├── bot_repository.py
│   │   │   ├── chat_repository.py
│   │   │   ├── inquiry_repository.py
│   │   │   ├── operator_repository.py
│   │   │   └── summary_repository.py
│   │   ├── websocket/
│   │   │   ├── chat_ws.py
│   │   │   └── connection_manager.py
│   │   └── middleware/
│   │       └── auth_middleware.py
│   ├── scripts/
│   │   └── create_sample_db.py  # サマリー確認用のサンプルDB生成
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_chat.py
│   │   ├── test_database.py
│   │   ├── test_inquiry.py
│   │   ├── test_inquiry_repository.py
│   │   ├── test_operator.py
│   │   ├── test_summary_repository.py
│   │   ├── test_summary_service.py
│   │   └── test_wait_time.py
│   └── requirements.txt
│
├── aidlc-docs/                  # AI-DLC ドキュメント（コードではない）
├── setup.sh                     # 環境セットアップスクリプト
├── .gitignore
└── README.md
```
