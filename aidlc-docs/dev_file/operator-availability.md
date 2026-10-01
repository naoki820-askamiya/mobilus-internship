# オペレータ稼働状態機能 仕様書

オペレータが自身の稼働状態を「稼働」「離席」から選択できるようにし、現在の推定待ち時間に利用する稼働オペレータ数へ反映する。

本機能の状態は待ち時間算出専用とし、問い合わせの担当取得、既存担当、チャット送受信には影響させない。

---

## 1. スコープ

### 1.1 対象

- オペレータ本人による「稼働」「離席」の状態確認・更新
- オペレータ向け全画面のナビゲーションバーへの状態表示・切替ボタン追加
- `GET /api/wait-time` が使用する稼働オペレータ数への状態反映
- `operators` テーブルへの状態カラム追加

### 1.2 対象外

- 離席中の新規担当取得禁止
- 離席中の担当取得ボタン無効化
- 既存担当やチャット送受信への制限
- 他オペレータによる状態変更
- 状態変更履歴の保存・参照
- 過去時点の稼働オペレータ数の復元
- `GET /api/wait-time/hourly` のモック値生成ロジック変更
- WebSocketによる状態配信

---

## 2. 用語・状態定義

| 項目 | 定義 |
|------|------|
| 稼働 | オペレータが待ち時間算出上の対応可能者として明示した状態 |
| 離席 | ログイン状態を維持したまま、待ち時間算出上の対応可能者から除外される状態 |
| 保存状態 | `operators.availability_status` に保存された状態 |
| 実効稼働 | 保存状態が「稼働」であり、かつ基準時刻に有効なセッションを1件以上持つこと |

状態値は既存のステータス表現に合わせて整数で管理する。

```text
OperatorAvailabilityStatus.AWAY = 0
OperatorAvailabilityStatus.AVAILABLE = 1
```

- 初期値は `AWAY` とし、オペレータ本人が明示的に切り替えた場合のみ `AVAILABLE` とする。
- 状態はオペレータ単位で保存し、複数タブ・複数端末で共有する。
- 最後に成功した更新を正とする。
- ログイン、ログアウト、セッション期限切れでは保存状態を変更しない。
- ログアウト中またはセッション期限切れのオペレータは、保存状態が `AVAILABLE` でも実効稼働には含めない。

---

## 3. データモデル

### 3.1 状態定数

`backend/app/models.py` に次の定数クラスを追加する。

```python
class OperatorAvailabilityStatus:
    AWAY = 0
    AVAILABLE = 1
```

`Operator` データクラスへ `availability_status: int` を追加する。

### 3.2 テーブル定義

`operators` テーブルへ `availability_status` を追加する。

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
```

| 制約 | 意図 |
|------|------|
| `NOT NULL` | 状態未設定を許可しない |
| `DEFAULT 0` | 本人が明示的に稼働へ切り替える前に、待ち時間を実態より短く算出することを防ぐ |
| `CHECK (availability_status IN (0, 1))` | DBへ不正な状態値が保存されることを防ぐ |

状態更新日時は保存しない。現在状態のみを扱い、履歴・監査・過去時点の復元を本機能の対象外とするためである。

### 3.3 DB再作成方針

本機能では `ALTER TABLE` による既存データ移行を行わず、開発DBを再作成する。

1. バックエンドを停止する。
2. `backend/app/database.py` の `CREATE_TABLES_SQL` を新定義へ変更する。
3. バックエンドの実行ディレクトリにある `chat_service.db` を削除する。
4. バックエンドを起動し、`init_db()` によりテーブルと初期オペレータを再作成する。

DB削除により、オペレータ、セッション、問い合わせ、メッセージを含む全データが失われる。実行前にデータ破棄が許容される開発環境であることを確認する。

本番データを保持する必要が生じた場合は、本仕様とは別にバージョン管理されたマイグレーションを設計する。

---

## 4. API契約

### 4.1 現在のオペレータ情報

既存のログインおよび本人情報取得レスポンスに `availability_status` を追加する。

| メソッド / パス | 認証 | 成功時 |
|-----------------|------|--------|
| `POST /api/auth/login` | 不要 | `200 OK` |
| `GET /api/auth/me` | 必須 | `200 OK` |

レスポンス例：

```json
{
  "id": 1,
  "username": "admin",
  "display_name": "管理者",
  "availability_status": 1
}
```

`GET /api/operators` および `POST /api/operators` のレスポンス契約は変更しない。

### 4.2 稼働状態更新

| 項目 | 内容 |
|------|------|
| メソッド / パス | `PATCH /api/auth/me/availability` |
| 認証 | 必須（Cookieセッション） |
| Content-Type | `application/json` |
| 成功時ステータス | `200 OK` |

本人以外の状態を変更できないよう、リクエストのパスおよびボディに `operator_id` を含めない。更新対象は認証済みセッションから決定する。

リクエスト例：

```json
{
  "availability_status": 0
}
```

成功レスポンス例：

```json
{
  "id": 1,
  "username": "admin",
  "display_name": "管理者",
  "availability_status": 0
}
```

同じ状態を指定した場合も成功とし、現在状態を返す。クライアント側で状態を反転させるだけのトグルAPIにはせず、遷移先を明示して更新を冪等にする。

### 4.3 スキーマ

`backend/app/schemas.py` に次を追加する。

```python
class CurrentOperatorResponse(OperatorResponse):
    availability_status: int = Field(..., ge=0, le=1)


class OperatorAvailabilityUpdateRequest(BaseModel):
    availability_status: int = Field(..., ge=0, le=1)
```

- `POST /api/auth/login`、`GET /api/auth/me`、`PATCH /api/auth/me/availability` は `CurrentOperatorResponse` を返す。
- オペレータ管理APIは既存の `OperatorResponse` を継続して使用する。

### 4.4 エラー

| 条件 | HTTPステータス | 挙動 |
|------|----------------|------|
| セッションなし・無効・期限切れ | `401 Unauthorized` | 状態を更新しない |
| `availability_status` が `0`、`1` 以外 | `422 Unprocessable Entity` | 状態を更新しない |
| リクエストボディ不正 | `422 Unprocessable Entity` | 状態を更新しない |

---

## 5. 待ち時間算出への反映

### 5.1 稼働オペレータ数の新定義

`GET /api/wait-time` の稼働オペレータ数 \(N\) を次のように変更する。

```text
N = availability_status が AVAILABLE であり、
    updated_at 時点で有効なセッションを持つ
    operator_id の重複なし件数
```

SQLの想定：

```sql
SELECT COUNT(DISTINCT sessions.operator_id)
FROM sessions
INNER JOIN operators
    ON operators.id = sessions.operator_id
WHERE sessions.expires_at > ?
  AND operators.availability_status = ?;
```

パラメータには同一リクエスト内で生成した `updated_at` と `OperatorAvailabilityStatus.AVAILABLE` を渡す。

### 5.2 計算式

推定待ち時間の計算式、対応中件数 \(A\)、待機件数 \(W\)、1人あたり同時対応数 \(P\)、想定対応時間 \(T\) は変更しない。

- 離席へ変更すると、次回の `GET /api/wait-time` から対象オペレータを \(N\) から除外する。
- 稼働へ変更すると、有効なセッションを持つ場合に限り、次回の `GET /api/wait-time` から \(N\) に含める。
- \(N = 0\) の場合は既存仕様どおり `estimated_wait_minutes = null` とする。
- `updated_at` は状態更新日時ではなく、待ち時間の算出基準時刻を引き続き表す。

### 5.3 業務機能へ影響させないこと

`availability_status` は次の判定に使用しない。

- `POST /api/inquiries/{inquiry_id}/assign` の担当取得可否
- 問い合わせ一覧の取得・表示
- オペレータ用WebSocketの接続可否
- 担当中問い合わせへのメッセージ送信可否
- 問い合わせ終了処理

---

## 6. バックエンド実装計画

| ファイル | 変更 |
|----------|------|
| `backend/app/database.py` | `operators` の新DDLを定義する |
| `backend/app/models.py` | `Operator.availability_status` と `OperatorAvailabilityStatus` を追加する |
| `backend/app/schemas.py` | `CurrentOperatorResponse` と `OperatorAvailabilityUpdateRequest` を追加する |
| `backend/app/repositories/operator_repository.py` | 本人の状態を更新し、更新後の `Operator` を返すメソッドを追加する |
| `backend/app/repositories/auth_repository.py` | 稼働人数集計を、operatorsとのJOINおよび稼働状態条件付きに変更する |
| `backend/app/services/operator_service.py` | 状態更新処理を追加する |
| `backend/app/routers/auth.py` | 状態更新APIを追加し、login/meのレスポンスへ状態を含める |
| `backend/tests/test_auth.py` | `Operator` のテストデータとlogin/meレスポンス検証を更新する |
| `backend/tests/test_database.py` | インメモリSQLiteで初期値とDB制約を検証する |
| `backend/tests/test_operator.py` | 状態更新サービスのテストを追加する |
| `backend/tests/test_wait_time.py` | 稼働状態条件を含む集計のテストを追加する |

### 6.1 リポジトリ

`OperatorRepository` に次の責務を追加する。

```text
update_availability(operator_id, availability_status)
    1. operators.availability_statusを更新
    2. 同一トランザクション内で更新後のOperatorを取得
    3. 更新後のOperatorを返す
```

SQLは必ずプレースホルダを使用し、状態値を文字列連結しない。

### 6.2 サービス

`OperatorService` に本人の状態更新処理を追加する。状態値のHTTP入力検証はPydanticスキーマで行い、サービスは認証済みオペレータIDと検証済み状態値をリポジトリへ渡す。

問い合わせサービスおよびチャットサービスには変更を加えない。

---

## 7. フロントエンド仕様

### 7.1 型

`frontend/src/types/index.ts` に認証済みオペレータ用の型を追加する。

```typescript
export const OPERATOR_AVAILABILITY_STATUS = {
  AWAY: 0,
  AVAILABLE: 1,
} as const;

export type OperatorAvailabilityStatus =
  typeof OPERATOR_AVAILABILITY_STATUS[keyof typeof OPERATOR_AVAILABILITY_STATUS];

export interface CurrentOperator extends Operator {
  availability_status: OperatorAvailabilityStatus;
}
```

`AuthContext` の `operator` は `CurrentOperator | null` とする。オペレータ管理画面で使用する既存の `Operator` 型は変更しない。

### 7.2 AuthContext

`frontend/src/contexts/AuthContext.tsx` に次を追加する。

```text
updateAvailability(status): Promise<void>
```

処理：

1. `PATCH /api/auth/me/availability` に遷移先の状態を送信する。
2. 成功レスポンスの `CurrentOperator` でContextの `operator` を置き換える。
3. 失敗時はContextの状態を変更せず、呼び出し元へエラーを送出する。

サーバーの成功レスポンスを状態の正とし、リクエスト完了前に表示を変更する楽観的更新は行わない。

### 7.3 UI配置

`frontend/src/components/OperatorNav.tsx` の右側へ、次の順番で配置する。

```text
[切替ボタン] [現在状態] [オペレータ表示名] [ログアウト]
```

現在状態を表示名の直前に置き、表示中のアカウントがどの状態にあるかを一まとまりとして把握できる配置とする。

表示例：

| 現在状態 | 状態表示 | 切替ボタン |
|----------|----------|------------|
| `AVAILABLE` | `稼働` | `離席にする` |
| `AWAY` | `離席` | `稼働にする` |

- 現在状態は色だけに依存せず、必ず「稼働」「離席」の文字列を表示する。
- ボタンには現在状態ではなく遷移先を表示する。
- 更新中は切替ボタンを無効化し、二重送信を防ぐ。
- 更新成功後に状態表示とボタン文言を切り替える。
- 更新失敗時は現在表示を維持し、ナビゲーション内または直下にエラーメッセージを表示する。
- エラー表示には `aria-live="polite"` を付与する。
- ログイン画面には状態UIを表示しない。

`OperatorNav` は全オペレータ画面で使用されているため、各ページへ個別の状態UIを追加しない。

### 7.4 複数タブ

状態はサーバーを正とし、複数タブから更新された場合は最後に成功した更新を採用する。リアルタイムなタブ間同期は本機能の対象外とし、各タブでは次回のページ再読み込みまたは認証情報再取得時に最新状態へ同期する。

---

## 8. 検証計画

### 8.1 DB・モデル

- DB再作成後、`operators.availability_status` が存在すること
- 初期オペレータの状態が `AWAY` であること
- 新規作成オペレータの状態が `AWAY` であること
- `NULL` および `0`、`1` 以外をDBへ保存できないこと
- `Operator(**dict(row))` で新カラムを含めて生成できること

### 8.2 API

- ログイン成功レスポンスに `availability_status` が含まれること
- `GET /api/auth/me` に `availability_status` が含まれること
- 認証済みで `PATCH /api/auth/me/availability` が `200` を返すこと
- `AVAILABLE` から `AWAY`、`AWAY` から `AVAILABLE` へ更新できること
- 同一状態の再送が成功すること
- 未認証時に `401` を返すこと
- `-1`、`2`、文字列、未指定で `422` を返すこと
- リクエストで他オペレータを更新できないこと

### 8.3 待ち時間

- 有効セッションかつ `AVAILABLE` のオペレータだけを数えること
- 有効セッションがあっても `AWAY` のオペレータを数えないこと
- `AVAILABLE` でも有効セッションがないオペレータを数えないこと
- 同一オペレータが複数の有効セッションを持っても1人として数えること
- 稼働人数が0人の場合に `estimated_wait_minutes = null` となること
- 既存の待ち時間計算式のテストが引き続き成功すること

### 8.4 フロントエンド

- 全オペレータ画面でナビゲーションに現在状態と切替ボタンが表示されること
- `AVAILABLE` では「稼働」「離席にする」と表示されること
- `AWAY` では「離席」「稼働にする」と表示されること
- 更新中にボタンが無効になること
- 成功レスポンス後に表示が切り替わること
- API失敗時に元の状態を維持し、エラーを表示すること
- 状態表示の追加後も表示名とログアウト操作が利用できること
- 離席中でも担当取得と既存チャットを利用できること

### 8.5 回帰

- バックエンドの全pytestを実行する。
- 変更対象ファイルのLintを実行する。
- オペレータのログイン、ログアウト、一覧、追加、削除が従来どおり動作することを確認する。
- `GET /api/wait-time/hourly` のレスポンスが変わらないことを確認する。

---

## 9. 受け入れ条件

- オペレータがナビゲーションから1回のボタン操作で「稼働」「離席」を切り替えられる。
- ナビゲーションに現在状態と遷移先が同時に表示される。
- 状態がDBへ保存され、ページ再読み込み後も維持される。
- 状態変更は認証中の本人にだけ適用される。
- 離席中のオペレータは現在の待ち時間算出における稼働人数から除外される。
- 稼働中でも有効なセッションがないオペレータは稼働人数に含まれない。
- 離席状態が担当取得、既存担当、チャット送受信へ影響しない。
- 状態値はDB制約とAPI入力検証の両方で `0`、`1` に限定される。
- DB再作成手順と全データ消失の注意事項が開発者に共有される。
- 既存の認証、問い合わせ、待ち時間、時系列待ち時間のテストに回帰がない。

---

## 10. 既存仕様書への反映

実装時に次のドキュメントも同期する。

| ドキュメント | 変更 |
|--------------|------|
| `aidlc-docs/dev_flie/wait-time-api.md` | 稼働オペレータ数 \(N\) の定義を「稼働状態かつ有効セッション」に変更する |
| `README.md` | 状態更新APIをAPI一覧へ追加する |
| `aidlc-docs/construction/chat-service/functional-design/domain-entities.md` | `Operator` エンティティとDDLへ状態を追加する |
| `aidlc-docs/construction/chat-service/functional-design/business-rules.md` | 状態が待ち時間だけに影響し、担当取得・チャットへ影響しないルールを追加する |

