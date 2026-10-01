# アプリケーション設計 統合ドキュメント

## 設計方針

| 項目 | 決定事項 |
|------|---------|
| フロントエンド構成 | 同一Reactアプリ（ルーティングで画面分離） |
| APIスタイル | REST API + WebSocket（別エンドポイント） |
| バックエンドアーキテクチャ | 3層構造（Router → Service → Repository） |
| WebSocket管理 | インメモリ管理 |
| フロントエンド状態管理 | useState / useContext のみ |
| BOT質問定義 | バックエンドコード（`app/bot/questions.py`）を正とする。DBには保存しない |
| グラフ | Recharts |

---

## システム全体構成

```
+------------------------------------------------------------------+
|                  React SPA (TypeScript)                           |
|                                                                  |
|  +------------------+  +----------+  +----------------+   |
|  | EndUserInquiry   |  | Operator |  | Operator       |   |
|  | (/)              |  | Login    |  | Dashboard      |   |
|  | 待ち時間+BOT+Chat |  |          |  | inquiries /    |   |
|  |                  |  |          |  | summary-board /|   |
|  |                  |  |          |  | users          |   |
|  +------------------+  +----------+  +----------------+   |
|                                                                  |
|  [AuthProvider] [useChat] [useBotChat]                           |
+-------------------+----------------------------------------------+
                    |
          HTTP + WebSocket
                    |
+-------------------v----------------------------------------------+
|              FastAPI Backend (Python)                             |
|                                                                  |
|  auth / chat / inquiry / operator / wait-time / summary / chat_ws|
|       |         |          |           |           |             |
|  Auth / Bot / Inquiry / Operator / WaitTime / Summary / Chat     |
|  Service                                                         |
|       |         |          |           |           |             |
|  Repositories + ConnectionManager + questions.py                 |
+-------------------+----------------------------------------------+
                    |
+-------------------v----------------------------------------------+
|                   SQLite DB                                       |
|  [operators] [sessions] [inquiries] [messages]                   |
+------------------------------------------------------------------+
```

---

## コンポーネント概要

### フロントエンド
| ID | コンポーネント | 主な責務 |
|----|--------------|---------|
| FE-001 | EndUserInquiry | エンドユーザの待ち時間確認・BOT事前質問・オペレータチャット |
| FE-002 | OperatorLogin | オペレータログイン画面 |
| FE-003 | InquiryList | 問い合わせ一覧（優先順、ページングなし） |
| FE-004 | InquiryDetail | 問い合わせ詳細チャット画面 |
| FE-005 | AppShell | ルーティング・認証管理 |
| FE-006 | OperatorAdd | オペレータ追加画面 |
| FE-007 | OperatorList | オペレータ一覧・削除画面 |
| FE-008 | （EndUserInquiry に統合） | 推定待ち時間と時系列グラフ |
| FE-009 | SummaryBoard | 日次セッション数と初回応答時間 |

### バックエンド
| ID | コンポーネント | 主な責務 |
|----|--------------|---------|
| BE-001 | auth | オペレータ認証・セッション管理・稼働状態更新 |
| BE-002 | inquiry | 問い合わせ管理・担当割り当て・未完了/完了済み一覧 |
| BE-003 | chat | リアルタイムメッセージ送受信 |
| BE-004 | connection_manager | WebSocket接続のインメモリ管理 |
| BE-005 | database | SQLite接続・テーブル作成・簡易マイグレーション |
| BE-006 | operator | オペレータ管理（追加・削除・一覧・稼働状態） |
| BE-007 | bot | BOT事前質問の開始・回答・状態遷移・料金計算 |
| BE-008 | wait_time | 推定待ち時間と時系列モック |
| BE-009 | summary | 日次セッション数と初回応答時間の集計 |

---

## API エンドポイント一覧

### REST API
| メソッド | パス | 説明 | 認証 |
|---------|------|------|------|
| POST | `/api/auth/login` | ログイン | 不要 |
| POST | `/api/auth/logout` | ログアウト | 不要（Cookieがあれば破棄） |
| GET | `/api/auth/me` | 自分の情報取得 | 必要 |
| PATCH | `/api/auth/me/availability` | 自分の稼働状態更新 | 必要 |
| POST | `/api/chat/start` | BOT事前質問開始（問い合わせ作成） | 不要 |
| POST | `/api/chat/{inquiry_id}/bot/answer` | BOT質問への回答 | 不要 |
| GET | `/api/inquiries` | 問い合わせ一覧（ページング、レガシー） | 必要 |
| GET | `/api/inquiries/open` | 未完了問い合わせ（優先順） | 必要 |
| GET | `/api/inquiries/closed` | 完了済み問い合わせ（最新50件） | 必要 |
| GET | `/api/inquiries/:id` | 問い合わせ詳細 | 必要 |
| GET | `/api/inquiries/:id/messages` | メッセージ一覧取得 | 必要 |
| POST | `/api/inquiries/:id/assign` | 担当取得 | 必要 |
| GET | `/api/operators` | オペレータ一覧取得 | 必要 |
| POST | `/api/operators` | オペレータ追加 | 必要 |
| DELETE | `/api/operators/:id` | オペレータ削除 | 必要 |
| GET | `/api/wait-time` | 推定待ち時間取得 | 不要 |
| GET | `/api/wait-time/hourly` | 1時間ごとの推定待ち時間（モック） | 不要 |
| GET | `/api/summary` | 日次サマリー取得 | 必要 |

### WebSocket
| パス | 説明 | 認証 |
|------|------|------|
| `ws://host/ws/chat/enduser/{inquiry_id}` | エンドユーザ用（作成済み問い合わせに接続） | 不要 |
| `ws://host/ws/chat/operator/{inquiry_id}` | オペレータ用 | 必要 |

---

## 画面一覧

| パス | 画面 | 認証 |
|------|------|------|
| `/` | エンドユーザ問い合わせ（待ち時間 → BOT → オペレータ） | 不要 |
| `/operator/login` | ログイン | 不要 |
| `/operator/inquiries` | 問い合わせ一覧 | 必要 |
| `/operator/inquiries/:id` | 問い合わせ詳細 | 必要 |
| `/operator/users` | オペレータ一覧 | 必要 |
| `/operator/users/add` | オペレータ追加 | 必要 |
| `/operator/summary-board` | サマリーボード | 必要 |

---

## 主要なビジネスルール

1. **担当割り当て排他制御**: `status=WAITING` かつ担当未設定の場合のみ担当を取得できる。BOT中は不可
2. **チャット送信権限**: 自分の担当する問い合わせのみメッセージ送信可能。BOT中の通常メッセージは拒否
3. **問い合わせ作成**: BOT開始APIで作成する。WebSocket接続時や初回メッセージでは作成しない
4. **セッション終了条件**: タブ閉じ / タイムアウト(30分) / 明示終了 / BOT完了
5. **ステータス算出**: ログイン中オペレータの視点で動的に算出する（BOT対応中を含む）
6. **稼働状態**: 待ち時間の稼働人数にのみ影響し、担当取得・チャットには影響しない
7. **一覧の並び**: 未完了は優先順全件、完了済みは最新50件

---

## 詳細設計ドキュメント参照

- コンポーネント定義詳細: [components.md](./components.md)
- メソッドシグネチャ: [component-methods.md](./component-methods.md)
- サービスオーケストレーション: [services.md](./services.md)
- 依存関係・データフロー: [component-dependency.md](./component-dependency.md)
