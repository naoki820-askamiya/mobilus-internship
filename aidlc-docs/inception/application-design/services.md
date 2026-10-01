# サービス定義

## サービス一覧

| サービス名 | 責務 | 依存先 |
|-----------|------|--------|
| AuthService | オペレータ認証・セッション管理 | AuthRepository |
| OperatorService | オペレータ追加・削除・一覧・稼働状態 | OperatorRepository |
| InquiryService | 問い合わせ一覧・担当割り当て・表示ステータス | InquiryRepository |
| ChatService | 通常メッセージ送受信・問い合わせ終了 | ChatRepository, InquiryRepository, ConnectionManager |
| BotService | BOT事前質問の開始・回答・状態遷移・料金計算 | BotRepository, InquiryRepository, questions.py, ConnectionManager |
| WaitTimeService | 推定待ち時間と時系列モック | InquiryRepository, AuthRepository |
| SummaryService | 日次セッション数と初回応答時間の集計 | SummaryRepository |

---

## AuthService

### 責務
- オペレータのログイン認証（ID/PWの検証）
- セッションの作成・破棄
- 認証状態の確認（期限切れセッションの削除を含む）

### オーケストレーション
```
1. ログインリクエスト受信
2. AuthRepository.find_operator_by_username() でオペレータ検索
3. パスワードハッシュ照合
4. 認証成功: AuthRepository.create_session() でセッション作成
5. セッションIDをクッキーに設定し、availability_status 付きで返却
```

### エラーハンドリング
- ユーザー未存在: 認証失敗エラー
- パスワード不一致: 認証失敗エラー
- セッション無効: 未認証エラー

---

## OperatorService

### 責務
- オペレータの追加（パスワード自動生成）
- 一覧取得・削除（自己削除禁止）
- 本人の稼働状態更新

稼働状態の更新は担当取得やチャット可否には使わない。待ち時間算出の稼働人数にのみ反映する。

---

## InquiryService

### 責務
- 未完了一覧の優先順ソート
- 完了済み一覧の件数制限
- 担当者の割り当て（排他制御）
- オペレータ視点の display_status 算出

### オーケストレーション

#### 未完了一覧
```
1. InquiryRepository.find_open() で status != CLOSED を全件取得
2. 各問い合わせの display_status を算出
3. DISPLAY_STATUS_PRIORITY で並べ、同順位は created_at / id の昇順
```

#### 担当割り当て
```
1. InquiryRepository.update_assignment() を WAITING かつ未割り当て条件で実行
2. 更新 0 件なら ConflictError
```

### エラーハンドリング
- 問い合わせ未存在: NotFoundエラー
- 既に担当あり / BOT中 / 終了済み: ConflictError

---

## ChatService

### 責務
- WebSocket経由の通常メッセージ送受信
- メッセージの永続化とブロードキャスト
- 問い合わせ終了（二重終了の防止）

### オーケストレーション

#### メッセージ送信
```
1. Inquiry を取得
2. CLOSED / BOT / bot_state != NULL なら拒否
3. オペレータは assigned_operator_id 一致が必須
4. 保存して broadcast
```

#### WebSocket接続管理
```
エンドユーザ接続:
1. 作成済み inquiry_id の存在と未終了を確認
2. ConnectionManager.connect() で登録
3. BOT中は切断検知用に保持し、通常メッセージは send_message 側で拒否
4. 切断時: close_inquiry()（既終了なら何もしない）

オペレータ接続:
1. セッション検証
2. 担当者でなければ拒否
3. ConnectionManager.connect() で登録
```

---

## BotService

### 責務
- BOT問い合わせの作成
- 回答検証と状態遷移
- 料金計算
- オペレータ移行 / 完了時のメッセージ保存

### オーケストレーション

#### 開始
```
1. questions.py から INQUIRY_CATEGORY を取得
2. BotRepository.create_bot_inquiry() で Inquiry と最初のBOTメッセージを作成
3. result=QUESTION を返却
```

#### 回答
```
1. status=BOT かつ bot_state 一致を確認（不一致は 409）
2. CHOICE / SIZE を検証（不正は 422）
3. 回答保存・次BOTメッセージ・status/bot_state 更新を同一トランザクションで実行
4. COMPLETED のときは ConnectionManager へ closed を broadcast
```

質問定義・選択肢・料金境界は `app/bot/questions.py` のみが保持する。

---

## WaitTimeService

### 責務
- 現在の推定待ち時間の算出（案B / 負荷 L 版）
- 前日営業時間帯のモック時系列生成

### オーケストレーション
```
1. updated_at = now_jst() を1回生成
2. A / W / N を取得（N は AVAILABLE かつ有効セッション）
3. L=A+W, C=N*P から切り上げ計算。N=0 は null
```

時系列は実集計ではなく `HOURLY_WAIT_TIME_MINUTES_BY_HOUR` を返す。

---

## SummaryService

### 責務
- 選択日のセッション数と平均初回応答時間の算出
- 0〜23時の欠けた時間帯の補完

未応答問い合わせはセッション数に含め、平均初回応答からは除外する。秒は四捨五入して整数にする。

---

## サービス間通信パターン

```
auth_router --------> AuthService --------> AuthRepository
                 \--> OperatorService ----> OperatorRepository

chat_router --------> BotService ---------> BotRepository
                                     \---> InquiryRepository
                                     \---> ConnectionManager

inquiry_router -----> InquiryService -----> InquiryRepository

operator_router ----> OperatorService ----> OperatorRepository

wait_time_router ---> WaitTimeService ----> InquiryRepository
                                     \---> AuthRepository

summary_router -----> SummaryService -----> SummaryRepository

chat_ws ------------> ChatService --------> ChatRepository
                                     \---> InquiryRepository
                                     \---> ConnectionManager
```

通信パターン:
- Router/WebSocket Handler → Service: 直接メソッド呼び出し
- Service → Repository: 直接メソッド呼び出し
- Service → ConnectionManager: 直接メソッド呼び出し
- BotService は InquiryService へ委譲せず、BotRepository で問い合わせを作成する
