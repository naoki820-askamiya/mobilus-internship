# 待ち時間 API 仕様書

エンドユーザがチャット開始前に参照する、推定待ち時間取得 API の契約・計算ロジック・実装計画を定義する。

元計画のレイヤ構成・認証方針・レスポンス契約は維持し、推定待ち時間の計算式のみ案B（負荷 \(L\) 版）に更新する。

---

## 1. API 契約

| 項目 | 内容 |
|------|------|
| メソッド / パス | `GET /api/wait-time` |
| 認証 | 不要（エンドユーザ向け公開 API） |
| 成功時ステータス | `200` |

### レスポンス

```json
{
  "estimated_wait_minutes": 5,
  "updated_at": "2026-08-17 18:30:00"
}
```

| フィールド | 型 | 説明 |
|------------|-----|------|
| `estimated_wait_minutes` | `int \| null` | 推定待ち時間（分）。オペレータが 0 人のときは算出不能として `null` |
| `updated_at` | `str` | 算出基準時刻。既存の `now_jst()` による `YYYY-MM-DD HH:MM:SS` 形式の JST 文字列 |

`updated_at` はセッション有効判定とレスポンスで同一の基準時刻を使い回す（算出中に時刻がずれないようにする）。

---

## 2. 用語・入力データ

| 記号 | 意味 | 取得方法 |
|------|------|----------|
| \(A\) | 対応中件数 | `status = InquiryStatus.ACTIVE` の件数 |
| \(W\) | 未対応（待機）件数 | `status = InquiryStatus.WAITING` かつ `assigned_operator_id IS NULL` の件数 |
| \(L\) | これから対応が必要な件数 | \(L = A + W\) |
| \(N\) | 稼働オペレータ数 | `updated_at` 時点で `expires_at > updated_at` のセッションから `COUNT(DISTINCT operator_id)` |
| \(P\) | 1人あたり同時対応数 | 定数 `CONCURRENT_INQUIRIES_PER_OPERATOR`（値: 2） |
| \(T\) | 1件あたり想定対応時間（分） | 定数 `ESTIMATED_MINUTES_PER_INQUIRY`（値: 5） |
| \(C\) | 総キャパシティ | \(C = N \times P\) |

### 集計ルール詳細

- **待機人数 \(W\)**: `status = InquiryStatus.WAITING` かつ `assigned_operator_id IS NULL`
- **対応中件数 \(A\)**: `status = InquiryStatus.ACTIVE`
- **オペレータ数 \(N\)**: 基準時刻 `updated_at` において有効なセッションを持つ `operator_id` の重複なし件数。同一オペレータの複数セッションは 1 人として扱う

---

## 3. 計算ロジック（案B / \(L\) 版）

意図: 対応中も未対応も「これから捌く仕事」として \(L\) にまとめ、キャパシティ \(C\) との差分だけを待ち時間にする。

\[
\text{estimated\_wait\_minutes} =
\begin{cases}
\texttt{null} & (N = 0) \\
0 & (N > 0 \land C > L) \\
\left\lceil \dfrac{(L - C) \times T}{C} \right\rceil & (N > 0 \land C \le L)
\end{cases}
\]

整数演算での切り上げ（既存実装と同じ方針）:

```text
# C > L のときは 0
# それ以外:
((L - C) * T + C - 1) // C
```

### 旧計画からの変更点

| 項目 | 旧計画 | 本仕様（案B） |
|------|--------|---------------|
| 入力 | \(W\), \(N\) のみ | \(A\), \(W\), \(N\)（\(L = A + W\)） |
| 空きがあるとき | 待機 0 人以外は常に正の値になり得る | \(C > L\) なら **0** |
| 満杯時の式 | \(\lceil W \times T / C \rceil\) | \(\lceil (L - C) \times T / C \rceil\) |
| オペレータ 0 人 | `null` | `null`（変更なし） |

### 計算例

定数: \(T = 5\), \(P = 2\)

| \(A\) | \(W\) | \(N\) | \(L\) | \(C\) | 結果 | 説明 |
|------|------|------|------|------|------|------|
| 0 | 0 | 1 | 0 | 2 | `0` | 負荷なし |
| 1 | 0 | 1 | 1 | 2 | `0` | キャパ内 |
| 2 | 0 | 1 | 2 | 2 | `0` | ちょうど満杯（超過なし） |
| 2 | 2 | 1 | 4 | 2 | `5` | \(\lceil (4-2)\times5/2 \rceil = 5\) |
| 0 | 3 | 1 | 3 | 2 | `3` | \(\lceil (3-2)\times5/2 \rceil = 3\) |
| 4 | 2 | 2 | 6 | 4 | `3` | \(\lceil (6-4)\times5/4 \rceil = 3\) |
| 任意 | 任意 | 0 | - | 0 | `null` | 算出不能 |

---

## 4. 実装計画

### 4.1 設定

`backend/app/config.py` に定数を追加し、計算式のマジックナンバーを避ける。

| 定数名 | 値 | 意味 |
|--------|-----|------|
| `ESTIMATED_MINUTES_PER_INQUIRY` | `5` | 1件あたり想定対応時間（分）\(T\) |
| `CONCURRENT_INQUIRIES_PER_OPERATOR` | `2` | オペレータ1人あたり同時処理係数 \(P\) |

### 4.2 リポジトリ

| ファイル | 変更 |
|----------|------|
| `backend/app/repositories/inquiry_repository.py` | 待機条件を SQL で集計する `count_waiting()` を追加 |
| 同上 | 対応中を SQL で集計する `count_active()` を追加（案Bで必要な \(A\)） |
| `backend/app/repositories/auth_repository.py` | 指定時刻より `expires_at` が後のセッションから `COUNT(DISTINCT operator_id)` を取得するメソッドを追加。同一オペレータの複数セッションは 1 人として扱う |

### 4.3 サービス

`backend/app/services/wait_time_service.py` を新設（または更新）し、次を集約する。

1. 基準時刻 `updated_at = now_jst()` の生成
2. \(A\)（`count_active`）、\(W\)（`count_waiting`）、\(N\)（有効セッションの重複なし件数）の取得
3. \(L = A + W\), \(C = N \times P\) の算出
4. 案Bによる切り上げ計算、および \(N = 0\) 時の `None` 返却
5. `WaitTimeResponse` の組み立て

### 4.4 スキーマ

`backend/app/schemas.py` に `WaitTimeResponse` を追加する。

- `estimated_wait_minutes: Optional[int]`
- `updated_at: str`

### 4.5 ルーター / エントリポイント

| ファイル | 変更 |
|----------|------|
| `backend/app/routers/wait_time.py` | 認証依存なしの GET ハンドラーからサービスを呼び出す |
| `backend/app/main.py` | ルーターを `prefix="/api/wait-time"` で登録 |

レイヤ責務は既存の inquiry / operator と同じ粒度とする（待ち時間は独立した公開リソースのため、operator ルーターには混ぜない）。

---

## 5. 検証計画

`backend/tests/test_wait_time.py` で次を検証する。

### 計算

- キャパ内（\(C > L\)）で `0`
- ちょうど満杯（\(C = L\)）で `0`
- 超過時の通常計算
- 端数の切り上げ
- オペレータ 0 人で `None`
- \(A\) と \(W\) を分けて与えても \(L = A + W\) として扱われること

### リポジトリ

- `count_waiting`: `WAITING` かつ未割り当てのみを数えること
- `count_active`: `ACTIVE` のみを数えること
- 有効セッション集計: `COUNT(DISTINCT operator_id)` と `expires_at > ?` を使うこと

### サービス

- セッション判定とレスポンスに同じ `updated_at` を使うこと

### API

- FastAPI のテストクライアントで `GET /api/wait-time` が `200` と仕様どおりのレスポンス形を返すこと

### 回帰

- backend の既存テスト・新規テスト・対象ファイルの Lint を実行し、回帰がないことを確認する

---

## 6. 既存実装との差分チェックリスト

既に旧計画どおり実装済みの場合、案B統合で追加・変更が必要な箇所は次のとおり。

| 対象 | 要否 | 内容 |
|------|------|------|
| `config.py` 定数 | 維持 | 変更なし |
| `count_waiting()` | 維持 | 変更なし |
| `count_active()` | **追加** | 対応中件数 \(A\) |
| 有効オペレータ集計 | 維持 | 変更なし |
| `WaitTimeService` 計算 | **変更** | \(L\) 版案Bに差し替え |
| `WaitTimeResponse` / router / main | 維持 | 契約は変更なし |
| `test_wait_time.py` | **更新** | 新式の期待値・`count_active` の検証を追加 |
