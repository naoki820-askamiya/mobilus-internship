# ドメインエンティティ定義

## エンティティ一覧

| エンティティ | 説明 |
|-------------|------|
| Operator | オペレータ（ログインユーザー） |
| Session | オペレータのログインセッション |
| Inquiry | 問い合わせ（BOT事前質問とオペレータ対応を含む会話単位） |
| Message | チャットメッセージ |
| InquiryFirstResponse | サマリーボード用の問い合わせごとの初回応答集計データ（永続化しない） |

---

## エンティティ詳細

### Operator（オペレータ）

| フィールド | 型 | 制約 | 説明 |
|-----------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | オペレータID |
| username | TEXT | UNIQUE, NOT NULL | ログインユーザー名 |
| password_hash | TEXT | NOT NULL | パスワードハッシュ |
| display_name | TEXT | NOT NULL | 表示名 |
| availability_status | INTEGER | NOT NULL, DEFAULT 0, CHECK | 稼働状態（0: 離席、1: 稼働） |
| created_at | TEXT | NOT NULL | 作成日時（JST） |

**稼働状態コード:**
| コード | 定数名 | 表示名 | 説明 |
|--------|--------|--------|------|
| 0 | `OperatorAvailabilityStatus.AWAY` | 離席 | 待ち時間算出上の稼働人数から除外 |
| 1 | `OperatorAvailabilityStatus.AVAILABLE` | 稼働 | 有効なセッションがある場合に稼働人数へ算入 |

初期値は `AWAY`。本人が明示的に切り替えた場合のみ `AVAILABLE` とする。ログイン・ログアウト・セッション期限切れでは変更しない。

---

### Session（ログインセッション）

| フィールド | 型 | 制約 | 説明 |
|-----------|------|------|------|
| id | TEXT | PK | セッションID（UUID v4、アプリケーション側で生成） |
| operator_id | INTEGER | FK(operators.id), NOT NULL | オペレータID |
| created_at | TEXT | NOT NULL | セッション作成日時（JST） |
| expires_at | TEXT | NOT NULL | セッション有効期限 |

有効期限は作成時刻 + 8時間（`SESSION_EXPIRY_SECONDS`）。

---

### Inquiry（問い合わせ）

| フィールド | 型 | 制約 | 説明 |
|-----------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | 問い合わせID |
| status | INTEGER | NOT NULL, DEFAULT 0 | ステータスコード |
| assigned_operator_id | INTEGER | FK(operators.id), NULLABLE | 担当オペレータID |
| created_at | TEXT | NOT NULL | 作成日時（JST） |
| closed_at | TEXT | NULLABLE | 終了日時 |
| bot_state | TEXT | NULLABLE | BOT質問の現在状態。`status=BOT` のときのみ値を持つ |

問い合わせは `POST /api/chat/start` で `status=BOT`、`bot_state=INQUIRY_CATEGORY` として作成する。オペレータ対応へ移行すると `status=WAITING`、`bot_state=NULL` になる。

**ステータスコード:**
| コード | 定数名 | 表示名 | 説明 |
|--------|--------|--------|------|
| 0 | `InquiryStatus.WAITING` | 担当者未決定 | BOTからオペレータ対応へ移行済みで、誰も担当していない |
| 1 | `InquiryStatus.ACTIVE` | 対応中（担当有り） | オペレータが担当し対応中 |
| 2 | `InquiryStatus.CLOSED` | 終了 | セッション終了済み |
| 3 | `InquiryStatus.BOT` | BOT対応中 | BOT事前質問の途中。担当取得・通常チャット不可 |

**BOT質問状態（`bot_state`）:**
| 値 | 説明 |
|----|------|
| `INQUIRY_CATEGORY` | 問い合わせ内容の選択 |
| `SIZE_QUESTION` | サイズ入力 |
| `PRICE_RESOLUTION` | 料金計算結果の表示と解決確認 |
| `ADDITIONAL_QUESTION` | 他の質問有無の確認 |
| `NULL` | BOT対応中ではない |

**オペレータから見たステータス表示（`DisplayStatus`）:**
| DB上のstatus | assigned_operator_id | display_status | 表示 |
|-------------|---------------------|----------------|------|
| 3 (BOT) | NULL | `bot` | 「BOT対応中」 |
| 0 (WAITING) | NULL | `waiting` | 「担当者未決定」 |
| 1 (ACTIVE) | 自分のID | `mine` | 「自分の担当」 |
| 1 (ACTIVE) | 他人のID | `others` | 「担当外」 |
| 2 (CLOSED) | 任意 | `closed` | 「終了」 |

未完了一覧の並び順は `DISPLAY_STATUS_PRIORITY` で一箇所管理する。

```text
mine → waiting → bot → others → closed
```

同じ優先度では作成日時の古い順、IDの昇順とする。完了済みは完了日時の新しい順、IDの降順で最大50件とする。

---

### Message（メッセージ）

| フィールド | 型 | 制約 | 説明 |
|-----------|------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | メッセージID |
| inquiry_id | INTEGER | FK(inquiries.id), NOT NULL | 問い合わせID |
| sender_type | INTEGER | NOT NULL | 送信者タイプコード |
| sender_name | TEXT | NULLABLE | 送信者表示名（オペレータ名、システムメッセージ用） |
| content | TEXT | NOT NULL | メッセージ内容 |
| created_at | TEXT | NOT NULL | 送信日時（JST） |

**sender_type コード:**
| コード | 定数名 | 説明 |
|--------|--------|------|
| 0 | `SenderType.ENDUSER` | エンドユーザからのメッセージ（BOT回答を含む） |
| 1 | `SenderType.OPERATOR` | オペレータからのメッセージ |
| 2 | `SenderType.SYSTEM` | システムメッセージ（退出通知等） |
| 3 | `SenderType.BOT` | BOTの質問・料金結果・案内 |

BOTの質問定義（選択肢・遷移条件）はDBに保存せず、`backend/app/bot/questions.py` で管理する。DBへ保存するのは、実際に表示したBOT文言とユーザの回答内容のみとする。

---

### InquiryFirstResponse（集計用）

永続テーブルではなく、サマリーボードの Repository が問い合わせ単位で返すデータクラス。

| フィールド | 型 | 説明 |
|-----------|------|------|
| id | int | 問い合わせID |
| created_at | str | 問い合わせ作成日時 |
| first_response_at | str \| None | 最初のオペレータメッセージ日時。未応答は `None` |

初回応答時間は `first_response_at - created_at`（秒、四捨五入した整数）。システム・エンドユーザ・BOTメッセージは応答に含めない。

---

## エンティティ間リレーション

```
+----------+       1:N        +---------+
| Operator | <-----------+    | Session |
+----------+             |    +---------+
     |                   |
     | 1:N               |
     v                   |
+---------+              |
| Inquiry | -------------+
+---------+    assigned_operator_id
     |
     | 1:N
     v
+---------+
| Message |
+---------+
```

- Operator 1:N Session（1人のオペレータが複数セッションを持ちうる）
- Operator 1:N Inquiry（1人のオペレータが複数の問い合わせを担当）
- Inquiry 1:N Message（1つの問い合わせに複数のメッセージ。BOT質問・回答も含む）

---

## データベーススキーマ（SQLite DDL）

```sql
CREATE TABLE IF NOT EXISTS operators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    availability_status INTEGER NOT NULL DEFAULT 0
        CHECK (availability_status IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,  -- アプリケーション側で UUID v4 を生成して INSERT
    operator_id INTEGER NOT NULL REFERENCES operators(id),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status INTEGER NOT NULL DEFAULT 0,  -- 0:waiting, 1:active, 2:closed, 3:bot
    assigned_operator_id INTEGER REFERENCES operators(id),
    created_at TEXT NOT NULL,
    closed_at TEXT,
    bot_state TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inquiry_id INTEGER NOT NULL REFERENCES inquiries(id),
    sender_type INTEGER NOT NULL,  -- 0:enduser, 1:operator, 2:system, 3:bot
    sender_name TEXT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_sessions_operator_id ON sessions(operator_id);
CREATE INDEX IF NOT EXISTS idx_inquiries_status ON inquiries(status);
CREATE INDEX IF NOT EXISTS idx_inquiries_assigned_operator_id ON inquiries(assigned_operator_id);
CREATE INDEX IF NOT EXISTS idx_inquiries_closed_order
    ON inquiries(status, closed_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_messages_inquiry_id ON messages(inquiry_id);
```

既存DBへ `bot_state` が無い場合は、`database.py` の `_migrate()` が `ALTER TABLE inquiries ADD COLUMN bot_state TEXT` を実行する。

### SQLite 固有の補足
- `INTEGER PRIMARY KEY AUTOINCREMENT`: SQLite では `INTEGER PRIMARY KEY` だけで自動採番されるが、`AUTOINCREMENT` を付けると過去のIDを再利用しないことを保証する
- `TEXT` 型: SQLite の TEXT にはサイズ制限がない。メッセージ長などの制約はアプリケーション層のバリデーションで行う
- 時刻カラム: SQLite には専用の日時型がないため、TEXT として `YYYY-MM-DD HH:MM:SS` 形式の JST 文字列で格納する
- **全時刻はアプリケーション側で JST 文字列を生成して INSERT する**（`DEFAULT CURRENT_TIMESTAMP` は使用しない）。`database.py` の `now_jst()` ヘルパーを使用する。形式は `%Y-%m-%d %H:%M:%S`（例: `2026-08-19 14:30:00`）で、タイムゾーンオフセットは付けない
- セッションID（UUID）: アプリケーション（Python）側で `uuid.uuid4()` により生成し、TEXT 型カラムに格納する
