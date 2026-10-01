# サマリーボード実装計画

## 1. 目的

認証済みオペレーターが、選択した日の問い合わせ状況と初回応答時間を確認できるサマリーボードを追加する。

表示する情報は以下の4項目とする。

- 選択日の合計セッション数
- 選択日の平均初回応答時間
- 1時間ごとのセッション数
- 1時間ごとの平均初回応答時間

## 2. 用語と集計仕様

この機能における「セッション」は、オペレーター認証用の `sessions` ではなく、チャット問い合わせを表す `inquiries` の1レコードとする。

### 2.1 セッション開始時刻

- `inquiries.created_at` を使用する。
- 現在の実装では、ユーザーが最初のメッセージを送信する直前に問い合わせが作成されるため、実質的にユーザーの初回メッセージ時刻を起点とする。
- DBに保存されているJSTの時刻を基準に、選択日の `00:00:00` 以上、翌日の `00:00:00` 未満を集計対象とする。

### 2.2 初回応答時間

問い合わせごとに、次の差を初回応答時間とする。

```text
最初のオペレーターメッセージの created_at - inquiries.created_at
```

- オペレーターメッセージは、既存の `SenderType.OPERATOR` に対応する `messages.sender_type` で判定する。
- システムメッセージとエンドユーザーメッセージは応答に含めない。
- オペレーターから一度も返信されていない問い合わせは、平均初回応答時間の分母・分子から除外する。
- 応答済み問い合わせが0件の場合、平均初回応答時間は `null` とする。
- APIでは秒単位の整数を返し、画面では「1分30秒」のように表示する。

### 2.3 時間帯別集計

- 問い合わせの `created_at` が属する時間帯（0時から23時）に集計する。
- セッション数は、該当時間帯に開始した問い合わせ数とする。
- 平均初回応答時間は、該当時間帯に開始した応答済み問い合わせの初回応答時間の平均とする。
- セッションがない時間帯も含め、APIは0時から23時までの24件を返す。
- セッション数が0件の場合は `session_count = 0` とする。
- 応答済み問い合わせが0件の場合は `average_first_response_seconds = null` とする。

## 3. 画面仕様

### 3.1 URLと認証

- 画面URL: `/operator/summary-board`
- 既存の `ProtectedRoute` で保護する。
- 未認証で直接アクセスした場合は `/operator/login` へリダイレクトする。
- APIも既存の `get_current_operator` を使用し、未認証の場合は `401 Unauthorized` を返す。
- `OperatorNav` に「サマリーボード」リンクを追加する。

### 3.2 画面構成

1. `OperatorNav`
2. ページタイトル「サマリーボード」
3. 日付選択欄
4. KPIカード
   - 合計セッション数
   - 平均初回応答時間
5. 1時間ごとのセッション数グラフ
6. 1時間ごとの平均初回応答時間グラフ

初期表示の日付はブラウザのJST基準の当日とし、`<input type="date">` で日付を変更できるようにする。日付変更時に集計APIを再取得する。

### 3.3 グラフ

既に導入されている Recharts を使用する。

- セッション数: `BarChart`
- 平均初回応答時間: `LineChart`
- X軸: 0時から23時
- セッション数のY軸: 件数
- 応答時間のY軸: 秒を受け取り、表示時に分・秒へ整形
- 平均値が `null` の時間帯は、0秒として描画せず欠損値として扱う。
- Tooltipには「時間帯」「セッション数」または「平均初回応答時間」を表示する。
- グラフには内容を説明する `aria-label` を設定する。

### 3.4 状態表示

- 読み込み中: ローディングメッセージを表示する。
- データ0件: KPIはセッション数0件、平均初回応答時間は「データなし」と表示する。
- APIエラー: エラーメッセージと再読み込みボタンを表示する。
- 日付変更時は以前の日付の集計値を残さず、選択中の日付と表示データが混在しないようにする。

## 4. API設計

### 4.1 エンドポイント

```http
GET /api/summary?date=2026-08-18
Cookie: session_id=...
```

- `date` は必須とし、FastAPI/Pydanticの `date` 型で検証する。
- 不正な日付の場合は `422 Unprocessable Entity` を返す。
- 集計対象が0件でも `200 OK` とし、空状態を表すレスポンスを返す。

### 4.2 レスポンス

```json
{
  "date": "2026-08-18",
  "total_sessions": 10,
  "average_first_response_seconds": 90,
  "hourly": [
    {
      "hour": 0,
      "session_count": 0,
      "average_first_response_seconds": null
    },
    {
      "hour": 1,
      "session_count": 2,
      "average_first_response_seconds": 75
    }
  ]
}
```

`hourly` は常に `hour = 0` から `hour = 23` までの24件を昇順で返す。

### 4.3 型

バックエンドに以下のPydanticモデルを追加する。

- `HourlySummaryResponse`
  - `hour: int`
  - `session_count: int`
  - `average_first_response_seconds: Optional[int]`
- `DailySummaryResponse`
  - `date: date`
  - `total_sessions: int`
  - `average_first_response_seconds: Optional[int]`
  - `hourly: List[HourlySummaryResponse]`

既存の `schemas.py` に合わせて、PythonのコレクションとNULL許容型には `List` と `Optional` を使用する。フロントエンドにも同じ構造のTypeScript型を追加し、APIレスポンスを型安全に扱う。

## 5. バックエンド実装

既存の Router → Service → Repository の構成に合わせて責務を分割する。

### 5.1 Repository

新規ファイル:

- `backend/app/repositories/summary_repository.py`

変更ファイル:

- `backend/app/models.py`
  - Repositoryの戻り値を型安全に扱うため、問い合わせID、問い合わせ作成時刻、初回応答時刻を保持する集計用dataclassを追加する。
  - 既存の `Inquiry`、`Message` と同様に、Repositoryから生の `sqlite3.Row` や辞書を返さない。

責務:

- 選択日の問い合わせを対象に集計する。
- 問い合わせごとに最初のオペレーターメッセージを取得する。
- 問い合わせ単位の集計用dataclassを返す。

初回応答は、問い合わせ単位で `MIN(messages.created_at)` を求めた後に平均する。メッセージ全件を直接平均しないようにする。

SQL方針:

```sql
SELECT
    i.id,
    i.created_at,
    MIN(m.created_at) AS first_response_at
FROM inquiries AS i
LEFT JOIN messages AS m
    ON m.inquiry_id = i.id
    AND m.sender_type = ?
WHERE i.created_at >= ?
  AND i.created_at < ?
GROUP BY i.id, i.created_at
ORDER BY i.created_at ASC, i.id ASC;
```

`sender_type` の値はSQLに `1` を直書きせず、既存の `SenderType.OPERATOR` をパラメータとして渡す。

文字列への `substr` 適用ではなく日付の開始・終了境界で絞り込み、将来 `created_at` にインデックスを追加した場合も利用しやすくする。

### 5.2 Service

新規ファイル:

- `backend/app/services/summary_service.py`

責務:

- Repositoryの取得結果から日次KPIを計算する。
- 0時から23時までの時間帯を生成し、欠けている時間帯を補完する。
- 応答済み問い合わせだけを平均初回応答時間の計算対象にする。
- 浮動小数点の秒数は四捨五入して整数にする。
- 既存Serviceと同様に `__init__` でRepositoryを生成し、`self.repository` に保持する。
- `DailySummaryResponse` を生成して返し、Routerには集計処理を持たせない。

時間帯数、1分あたりの秒数などは名前付き定数にし、マジックナンバーを避ける。

### 5.3 Router

新規ファイル:

- `backend/app/routers/summary.py`

責務:

- `GET /api/summary` を公開する。
- クエリパラメータの日付を検証する。
- `Depends(get_current_operator)` で認証する。
- 既存の一覧APIと同様に、モジュールスコープで `SummaryService` を生成する。
- Serviceが返した `DailySummaryResponse` をそのまま返し、Routerを薄く保つ。

変更ファイル:

- `backend/app/main.py`: `summary_router` を `/api/summary` で登録する。
- `backend/app/schemas.py`: 集計レスポンスモデルを追加する。

DBカラム追加は不要とする。データ量が増えて集計が遅くなる場合に備え、以下の複合インデックス追加を検討する。

```sql
CREATE INDEX IF NOT EXISTS idx_inquiries_created_at
    ON inquiries(created_at);

CREATE INDEX IF NOT EXISTS idx_messages_sender_inquiry_created
    ON messages(sender_type, inquiry_id, created_at);
```

## 6. フロントエンド実装

### 6.1 新規ファイル

- `frontend/src/pages/SummaryBoard.tsx`
  - 選択日、読み込み状態、エラー、集計結果を管理する。
  - `credentials: 'include'` を指定して集計APIを呼び出す。
- `frontend/src/pages/SummaryBoard.module.css`
  - 日付選択欄、KPIカード、グラフ領域、レスポンシブ表示を定義する。
- `frontend/src/components/HourlySessionChart.tsx`
  - 1時間ごとのセッション数を棒グラフで表示する。
- `frontend/src/components/HourlyResponseTimeChart.tsx`
  - 1時間ごとの平均初回応答時間を折れ線グラフで表示する。
- 必要に応じて各グラフのCSS Moduleを追加する。

### 6.2 変更ファイル

- `frontend/src/App.tsx`
  - `/operator/summary-board` を追加し、`ProtectedRoute` でラップする。
  - 画面の初期読み込みを軽量化するため、`SummaryBoard` を `lazy` と `Suspense` で遅延読み込みする。
- `frontend/src/components/OperatorNav.tsx`
  - 「サマリーボード」へのリンクを追加する。
- `frontend/src/types/index.ts`
  - `HourlySummaryResponse` と `DailySummaryResponse` を追加する。

日付処理と応答時間表示はページ内に重複実装せず、必要に応じて小さなユーティリティ関数へ分離する。

## 7. テスト計画

### 7.1 Repositoryテスト

新規ファイル:

- `backend/tests/test_summary_repository.py`

確認項目:

- 選択日の境界 `00:00:00` を含む。
- 翌日の `00:00:00` を含まない。
- 他の日の問い合わせが混ざらない。
- 複数のオペレーターメッセージがある場合、最初の1件だけを採用する。
- エンドユーザーおよびシステムメッセージを応答として扱わない。
- 未応答の問い合わせもセッション数には含める。

一時SQLite DBを使用し、実DBの内容に依存しないテストにする。

### 7.2 Serviceテスト

新規ファイル:

- `backend/tests/test_summary_service.py`

確認項目:

- 合計セッション数を正しく算出する。
- 日次の平均初回応答時間を正しく算出する。
- 時間帯別の件数と平均を正しく算出する。
- 未応答問い合わせを応答時間の平均から除外する。
- 全件未応答の場合、平均が `null` になる。
- データ0件の場合も24時間分のデータを返す。
- 秒数を仕様どおり整数へ丸める。
- 既存Serviceテストと同様にRepositoryクラスをモックし、生成したServiceの `repository` をモックへ差し替える。

### 7.3 Router・認証テスト

確認項目:

- 認証済みの場合は `200` を返す。
- 未認証の場合は `401` を返す。
- 不正な日付の場合は `422` を返す。

### 7.4 フロントエンド確認

現状はフロントエンドの自動テスト基盤がないため、`npm run build` による型チェックと手動確認を行う。

- 未ログインで画面URLへアクセスするとログイン画面へ遷移する。
- ログイン後、ナビゲーションから画面へ遷移できる。
- 初期表示で当日の集計が表示される。
- 日付を変更すると全KPI・グラフが更新される。
- データ0件、応答0件、APIエラーが適切に表示される。
- 画面幅が狭い場合もKPIとグラフが閲覧できる。

## 8. 実装順序

1. 集計仕様とAPIレスポンス型を確定する。
2. `SummaryRepository` とRepositoryテストを実装する。
3. `SummaryService` とServiceテストを実装する。
4. レスポンススキーマ、Router、認証テストを実装する。
5. `main.py` に集計APIを登録する。
6. フロントエンドのAPI型を追加する。
7. `SummaryBoard` と2種類のグラフを実装する。
8. 認証必須ルートとナビゲーションを追加する。
9. バックエンド全テストと `npm run build` を実行する。
10. 実データで日付境界、未応答、複数時間帯の表示を確認する。

## 9. 完了条件

- 認証済みオペレーターだけがサマリーボードを閲覧できる。
- 選択日の合計セッション数と平均初回応答時間が正しく表示される。
- 0時から23時までのセッション数と平均初回応答時間をグラフで確認できる。
- 未応答セッションをセッション数には含め、応答時間の平均からは除外できる。
- データがない日や応答がない時間帯をエラーにせず表示できる。
- APIの日付検証と認証が機能する。
- バックエンドの追加テスト、既存テスト、フロントエンドビルドが成功する。
