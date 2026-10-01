# フロントエンドコンポーネント設計

## コンポーネント階層構造

```
App
├── AuthProvider（認証コンテキスト）
│   ├── [Route: /] EndUserInquiry
│   │   ├── WaitTimeChart（入口フェーズ）
│   │   ├── ChatWindow（チャットフェーズ）
│   │   │   └── MessageBubble（繰り返し）
│   │   ├── BotQuestionInput（BOT対応中）
│   │   │   ├── ChoiceQuestion（type=CHOICE）
│   │   │   └── SizeQuestion（type=SIZE）
│   │   ├── MessageInput（オペレータ対応中）
│   │   ├── ConnectionStatus
│   │   └── EndButton
│   │
│   ├── [Route: /operator/login] OperatorLogin
│   │   ├── LoginForm
│   │   └── ErrorMessage
│   │
│   └── [ProtectedRoute: /operator/*]
│       ├── OperatorNav（稼働状態切替・ログアウト）
│       ├── [Route: /operator/inquiries] InquiryList
│       │   ├── InquiryTable
│       │   │   ├── InquiryRow（繰り返し）
│       │   │   │   ├── StatusBadge
│       │   │   │   └── AssignButton（担当者未決定のみ）
│       │   │   └── EmptyState
│       │   └── 完了済み件数の案内文
│       │
│       ├── [Route: /operator/inquiries/:id] InquiryDetail
│       │   ├── InquiryInfo
│       │   ├── ChatWindow
│       │   │   └── MessageBubble（繰り返し）
│       │   └── MessageInput（担当者のみ有効）
│       │
│       ├── [Route: /operator/users/add] OperatorAdd
│       │   └── OperatorAddForm
│       │
│       ├── [Route: /operator/users] OperatorList
│       │   ├── OperatorAddButton（「+ オペレータを追加」ボタン）
│       │   ├── OperatorTable
│       │   │   └── OperatorRow（繰り返し）
│       │   └── EmptyState
│       │
│       └── [Route: /operator/summary-board] SummaryBoard（lazy）
│           ├── 日付選択
│           ├── KPIカード
│           ├── HourlySessionChart
│           └── HourlyResponseTimeChart
```

`SummaryBoard` は初期読み込みを軽くするため `lazy` + `Suspense` で遅延読み込みする。

---

## ページごとの Props / State 定義

### EndUserInquiry

**State:**
| 名前 | 型 | 初期値 | 説明 |
|------|------|--------|------|
| hasStartedChat | boolean | false | チャット開始済みか |
| waitTime | WaitTimeResponse \| null | null | 現在の推定待ち時間 |
| waitTimeHistory | WaitTimeHistoryResponse \| null | null | 時系列待ち時間 |
| isWaitTimeLoading | boolean | true | 現在値の初回取得中 |
| isHistoryLoading | boolean | true | 時系列の取得中 |
| waitTimeError | string \| null | null | 現在値のエラー |
| historyError | string \| null | null | 時系列のエラー |
| isClosed | boolean | false | セッション終了フラグ |

**State / フック（チャット）:**
| 名前 | 型 | 説明 |
|------|------|------|
| useBotChat | フック | BOT開始・回答・phase / question / messages |
| useChat | フック | WebSocket接続・通常メッセージ |

**phase:** `STARTING` / `BOT` / `OPERATOR` / `COMPLETED` / `ERROR`

**API連携:**
- GET `/api/wait-time`（入口フェーズ中、1分間隔で再取得）
- GET `/api/wait-time/hourly`（入口フェーズ表示時に1回）
- POST `/api/chat/start`（「チャットを開始する」押下後）
- POST `/api/chat/{inquiry_id}/bot/answer`
- WebSocket: `ws://host/ws/chat/enduser/{inquiry_id}`（BOT開始後に接続）

---

### OperatorLogin

**State:**
| 名前 | 型 | 初期値 | 説明 |
|------|------|--------|------|
| username | string | '' | ユーザー名入力 |
| password | string | '' | パスワード入力 |
| error | string \| null | null | エラーメッセージ |
| isLoading | boolean | false | ログイン処理中フラグ |

**API連携:**
- POST `/api/auth/login`

---

### InquiryList

**State:**
| 名前 | 型 | 初期値 | 説明 |
|------|------|--------|------|
| inquiries | InquiryWithStatus[] | [] | 未完了 + 完了済みを結合した一覧 |
| isLoading | boolean | false | データ取得中フラグ |
| hasNewInquiry | boolean | false | 新着問い合わせ通知フラグ |

ページングは行わない。完了済みは最新50件までの案内を表示する。

**API連携:**
- GET `/api/inquiries/open`
- GET `/api/inquiries/closed`
- POST `/api/inquiries/:id/assign`
- 5秒間隔の新着検知は `/api/inquiries/open` のみ

---

### InquiryDetail

**State:**
| 名前 | 型 | 初期値 | 説明 |
|------|------|--------|------|
| inquiry | InquiryWithStatus \| null | null | 問い合わせ情報 |
| historyMessages | Message[] | [] | RESTで取得した履歴 |
| canSend | boolean | false | 自分の担当かつ接続中のみ true |

**使用フック:** useChat

**API連携:**
- GET `/api/inquiries/:id`
- GET `/api/inquiries/:id/messages`
- WebSocket: `ws://host/ws/chat/operator/{inquiry_id}`（`display_status === 'mine'` のときのみ）

BOT対応中は入力欄を無効化し、「BOTが対応中です。完了までお待ちください」を表示する。

---

### SummaryBoard

**State:**
| 名前 | 型 | 初期値 | 説明 |
|------|------|--------|------|
| selectedDate | string | JST当日 | 集計対象日 |
| summary | DailySummaryResponse \| null | null | 集計結果 |
| isLoading | boolean | true | 取得中 |
| error | string \| null | null | エラーメッセージ |

**API連携:**
- GET `/api/summary?date=YYYY-MM-DD`

---

## 共通コンポーネント Props

### ChatWindow
| Props | 型 | 説明 |
|-------|------|------|
| messages | Message[] | 表示するメッセージ一覧 |
| currentUserType | 'enduser' \| 'operator' | メッセージの左右配置判定用 |

### MessageInput
| Props | 型 | 説明 |
|-------|------|------|
| onSend | (content: string) => void | 送信コールバック |
| disabled | boolean | 無効状態（終了済み/担当外/BOT中） |
| placeholder | string | プレースホルダーテキスト |

### MessageBubble
| Props | 型 | 説明 |
|-------|------|------|
| message | Message | メッセージデータ |
| isOwn | boolean | 自分のメッセージかどうか |
| viewMode | 'enduser' \| 'operator' | 表示モード。BOTは「🤖 自動応答」、エンドユーザ画面のオペレータは「🎧 サポート」 |

### BotQuestionInput
| Props | 型 | 説明 |
|-------|------|------|
| question | BotQuestion | 現在回答可能な質問 |
| disabled | boolean | 送信中は true |
| error | string \| null | 回答失敗時のメッセージ |
| onAnswer | (payload: BotAnswerPayload) => void | 回答送信 |

### StatusBadge
| Props | 型 | 説明 |
|-------|------|------|
| status | 'waiting' \| 'mine' \| 'others' \| 'closed' \| 'bot' | 表示ステータス |

ラベル: 担当者未決定 / 自分の担当 / 担当外 / 終了 / BOT対応中

### AssignButton
| Props | 型 | 説明 |
|-------|------|------|
| inquiryId | number | 問い合わせID |
| onAssign | (inquiryId: number) => void | 担当取得コールバック |
| disabled | boolean | 無効状態 |

### ConnectionStatus
| Props | 型 | 説明 |
|-------|------|------|
| isConnected | boolean | 接続状態 |

### EndButton
| Props | 型 | 説明 |
|-------|------|------|
| onEnd | () => void | 終了コールバック |
| disabled | boolean | 無効状態 |

### OperatorNav
稼働状態切替・現在状態・表示名・ログアウトを右側に配置する。リンクは問い合わせ一覧 / サマリーボード / オペレータ管理。

---

## ユーザーインタラクションフロー

### エンドユーザのフロー
```
1. 問い合わせ画面 (/) で待ち時間を確認
2. 「チャットを開始する」を押下（同一ページ内でチャットフェーズへ切り替え）
3. POST /api/chat/start で問い合わせ作成 + 最初のBOT質問
4. 作成済み inquiry_id で WebSocket 接続
5. BOT質問に回答（選択肢 or サイズ入力）
6a. オペレータ対応へ移行 → MessageInput で通常チャット
6b. BOTだけで解決 → 終了表示
7. 会話継続 or 「終了」ボタン押下
8. セッション終了 → 送信無効化
```

### オペレータのフロー
```
1. ログイン画面 (/operator/login) → ID/PW入力 → ログイン
2. 問い合わせ一覧 (/operator/inquiries) 表示
   - 優先順: 自分の担当 → 未対応 → BOT対応中 → 担当外 → 完了済み（最新50件）
3. 「担当者未決定」の問い合わせで「担当する」を押下
4. 問い合わせ詳細 (/operator/inquiries/:id) に遷移
5. 自分の担当なら WebSocket 接続しチャット開始
6. セッション終了 → 送信無効化。履歴（BOT含む）は閲覧可能
7. ナビゲーションから稼働/離席切替、サマリーボード、オペレータ管理が可能
```

---

## フォームバリデーション

### ログインフォーム
| フィールド | バリデーション | エラーメッセージ |
|-----------|--------------|----------------|
| username | 必須 | 「ユーザー名を入力してください」 |
| password | 必須 | 「パスワードを入力してください」 |
| API応答 | 401 | 「ユーザー名またはパスワードが正しくありません」 |

### メッセージ入力
| フィールド | バリデーション | エラーメッセージ |
|-----------|--------------|----------------|
| content | 必須、空白のみ不可 | （送信ボタンを無効化で対応） |

### BOTサイズ入力
| フィールド | バリデーション | エラーメッセージ |
|-----------|--------------|----------------|
| 縦・横・高さ | 必須、1〜1000 の整数 | 送信前に入力欄で制御。APIは 422 |

### オペレータ追加フォーム
| フィールド | バリデーション | エラーメッセージ |
|-----------|--------------|----------------|
| username | 必須 | 「ユーザー名を入力してください」 |
| display_name | 必須 | 「表示名を入力してください」 |
| API応答 | 409 | 「このユーザー名は既に使用されています」 |

---

## 型定義（TypeScript）

```typescript
export const INQUIRY_STATUS = {
  WAITING: 0,
  ACTIVE: 1,
  CLOSED: 2,
  BOT: 3,
} as const;

export const SENDER_TYPE = {
  ENDUSER: 0,
  OPERATOR: 1,
  SYSTEM: 2,
  BOT: 3,
} as const;

export const OPERATOR_AVAILABILITY_STATUS = {
  AWAY: 0,
  AVAILABLE: 1,
} as const;

export interface Operator {
  id: number;
  username: string;
  display_name: string;
}

export interface CurrentOperator extends Operator {
  availability_status: 0 | 1;
}

export interface Message {
  id: number;
  inquiry_id: number;
  sender_type: number; // 0:enduser, 1:operator, 2:system, 3:bot
  sender_name: string | null;
  content: string;
  created_at: string; // YYYY-MM-DD HH:MM:SS
}

export type BotStateName =
  | 'INQUIRY_CATEGORY'
  | 'SIZE_QUESTION'
  | 'PRICE_RESOLUTION'
  | 'ADDITIONAL_QUESTION';

export interface Inquiry {
  id: number;
  status: number; // 0:waiting, 1:active, 2:closed, 3:bot
  assigned_operator_id: number | null;
  created_at: string;
  closed_at: string | null;
  bot_state: BotStateName | null;
}

export type DisplayStatus = 'waiting' | 'mine' | 'others' | 'closed' | 'bot';

export interface InquiryWithStatus extends Inquiry {
  display_status: DisplayStatus;
}

export interface WaitTimeResponse {
  estimated_wait_minutes: number | null;
  updated_at: string;
}

export interface WaitTimeHistoryResponse {
  updated_at: string;
  items: Array<{ time: string; estimated_wait_minutes: number }>;
}

export interface DailySummaryResponse {
  date: string;
  total_sessions: number;
  average_first_response_seconds: number | null;
  hourly: Array<{
    hour: number;
    session_count: number;
    average_first_response_seconds: number | null;
  }>;
}

export type BotQuestionType = 'CHOICE' | 'SIZE';
export type BotResultType = 'QUESTION' | 'OPERATOR' | 'COMPLETED';

export interface BotQuestion {
  message_id: number;
  state: BotStateName;
  type: BotQuestionType;
  text: string;
  options: Array<{ value: string; label: string }>;
}

export interface BotStepResponse {
  inquiry_id: number;
  result: BotResultType;
  messages: Message[];
  question: BotQuestion | null;
}

export interface BotAnswerPayload {
  type: BotQuestionType;
  value?: string;
  length_cm?: number;
  width_cm?: number;
  height_cm?: number;
}
```
