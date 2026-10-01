# ビジネスロジックモデル

## 1. 認証フロー

### ログイン
```
1. オペレータがユーザー名とパスワードを入力
2. AuthService.login(username, password) を呼び出し
3. AuthRepository.find_operator_by_username(username) でオペレータ検索
4. オペレータ未存在 → 認証失敗エラー返却
5. bcrypt でパスワードハッシュ照合
6. パスワード不一致 → 認証失敗エラー返却
7. AuthRepository.create_session(operator_id) でセッション作成
   - session_id = UUID v4 を生成
   - expires_at = 現在時刻 + 8時間
8. レスポンスの Set-Cookie ヘッダーに session_id を設定
9. オペレータ情報（availability_status を含む CurrentOperator）を返却
```

### ログアウト
```
1. リクエストのCookieから session_id を取得
2. AuthRepository.delete_session(session_id) でセッション削除
3. レスポンスの Set-Cookie でCookieをクリア
4. 稼働状態は変更しない
```

### 認証確認（ミドルウェア）
```
1. リクエストのCookieから session_id を取得
2. session_id が無い → 未認証エラー(401)
3. AuthRepository.get_session(session_id) でセッション取得
4. セッション未存在 or 有効期限切れ → 未認証エラー(401)
5. セッションからoperator_idを取得しリクエストコンテキストに設定
```

### 稼働状態の更新
```
1. オペレータがナビゲーションの切替ボタンを押下
2. PATCH /api/auth/me/availability { availability_status }
3. OperatorService.update_availability(operator_id, status) を呼び出し
4. OperatorRepository で本人の状態を更新し、更新後の Operator を返却
5. AuthContext の operator を成功レスポンスで置き換える（楽観的更新はしない）
```

---

## 2. 問い合わせライフサイクル

### 問い合わせ作成（BOT開始時）
```
1. エンドユーザがチャット画面 (/) を開く
2. POST /api/chat/start を呼び出し
3. BotService.start() が Inquiry を status=BOT、bot_state=INQUIRY_CATEGORY で作成
4. 最初のBOT質問を messages に保存（sender_type=BOT）
5. inquiry_id と質問を返却
6. フロントエンドが作成済み inquiry_id で WebSocket 接続する
```

既存の「初回チャットメッセージ送信時」や「WebSocket接続時」の問い合わせ作成は使用しない。

### BOT回答と状態遷移
```
1. エンドユーザが現在の質問に回答する
2. POST /api/chat/{inquiry_id}/bot/answer を呼び出し
3. Inquiry が status=BOT であること、DBの bot_state とリクエストの state が一致することを確認
4. 回答形式と値を検証する
5. ユーザ回答の保存、次BOTメッセージの保存、status / bot_state の更新を同一トランザクションで行う
6. result に応じて遷移する
   - QUESTION: 次の質問UIを表示
   - OPERATOR: status=WAITING、bot_state=NULL。通常の MessageInput へ切り替え
   - COMPLETED: 既存の終了処理相当で閉じ、WebSocket へ closed を通知
```

### 問い合わせ担当取得
```
1. オペレータが「担当する」ボタンを押下
2. InquiryService.assign_operator(inquiry_id, operator_id) を呼び出し
3. InquiryRepository.update_assignment() が
   WHERE assigned_operator_id IS NULL AND status = WAITING で更新
4. 更新失敗（BOT中・既に担当あり・終了済み） → ConflictError（409）
5. 更新された Inquiry を返却
```

### 問い合わせ終了
```
1. 終了イベント発生（タブ閉じ / タイムアウト / 明示終了 / BOT完了）
2. inquiry.status を CLOSED に更新し、bot_state を NULL、closed_at を設定
3. 既に終了済みなら何もしない
4. 明示終了・タブ閉じ・タイムアウトではシステムメッセージ「ユーザーが退出しました」を保存
5. 接続中の相手にメッセージと closed をブロードキャスト
6. エンドユーザのWebSocket接続を切断
```

### 問い合わせ一覧取得
```
未完了:
1. GET /api/inquiries/open
2. InquiryRepository.find_open() で status != CLOSED を全件取得
3. ログイン中オペレータ視点で display_status を算出し、DISPLAY_STATUS_PRIORITY で並べる
4. 同じ優先度は created_at 昇順、id 昇順

完了済み:
1. GET /api/inquiries/closed
2. InquiryRepository.find_recent_closed(limit=50) で完了日時の新しい順に取得
3. display_status は closed

表示ステータス:
   - status == BOT → bot（BOT対応中）
   - status == WAITING → waiting（担当者未決定）
   - status == ACTIVE AND assigned_operator_id == operator_id → mine（自分の担当）
   - status == ACTIVE AND assigned_operator_id != operator_id → others（担当外）
   - status == CLOSED → closed（終了）
```

---

## 3. チャットメッセージフロー

### BOT質問・回答
```
1. BOT質問は HTTP レスポンスの messages / question でフロントへ返す
2. WebSocket では BOT質問を重複配信しない
3. ユーザ回答も API が保存した Message をフロントが一覧へ追加する
```

### エンドユーザからの通常メッセージ送信
```
1. エンドユーザがWebSocket経由でメッセージ送信（オペレータ対応へ移行後）
2. ChatService.send_message(inquiry_id, ENDUSER, content) を呼び出し
3. 問い合わせのステータス確認:
   - status == CLOSED → 拒否
   - status == BOT または bot_state != NULL → 拒否
4. Message を保存し、ConnectionManager.broadcast() で全接続に配信
```

### オペレータからのメッセージ送信
```
1. オペレータがWebSocket経由でメッセージ送信
2. ChatService.send_message(...) を呼び出し
3. 権限確認: assigned_operator_id が送信者と一致すること
4. ステータス確認: CLOSED / BOT では拒否
5. sender_name=operator.display_name で保存し、ブロードキャスト
```

### メッセージ履歴取得
```
1. GET /api/inquiries/:id/messages を呼び出し
2. 認証確認（オペレータのみ）
3. InquiryRepository.find_messages_by_inquiry_id() で全メッセージ取得（id 昇順）
4. BOT質問・回答を含む履歴を返却
```

---

## 4. セッション管理フロー

### セッション終了: 明示的な「終了」ボタン
```
1. エンドユーザが「終了」ボタンを押下
2. WebSocket経由で終了イベントをサーバーに送信
3. サーバーが問い合わせ終了処理を実行
4. エンドユーザ画面に「チャットが終了しました」を表示
```

### セッション終了: タブ閉じ
```
1. ブラウザのタブが閉じられる
2. WebSocket接続が切断される
3. サーバーが切断を検知し、問い合わせ終了処理を実行
```

### セッション終了: タイムアウト（30分）
```
1. ConnectionManager がエンドユーザ接続の最終アクティビティを保持
2. 最後のメッセージ送信から30分経過を検知
3. 問い合わせ終了処理を実行し、接続を切断
```

### タイムアウト実装方式
- 各問い合わせの最終アクティビティ時刻を `ConnectionManager` でインメモリ管理
- `get_timed_out_inquiries(timeout_seconds)` でタイムアウト対象を取得
- タイムアウト閾値は `TIMEOUT_SECONDS`（デフォルト30分）

---

## 5. オペレータ管理フロー

### オペレータ追加
```
1. ログイン済みオペレータがオペレータ管理画面の「+ オペレータを追加」ボタンを押下
2. username（ログインID）と display_name（表示名）を入力
3. POST /api/operators を呼び出し
4. OperatorService.create_operator(username, display_name) を呼び出し
5. username の重複チェック:
   - 重複あり → ConflictError（409）を返却
6. パスワード自動生成（英数字12文字ランダム）
7. bcrypt でパスワードハッシュ化
8. OperatorRepository.create(operator) でDB保存（availability_status は DEFAULT 0 = AWAY）
9. 生成されたパスワード（平文）をレスポンスとして返却
10. フロントエンドでパスワードを画面に表示
```

### オペレータ一覧取得
```
1. GET /api/operators を呼び出し
2. OperatorService.list_operators() を呼び出し
3. オペレータ一覧を返却（パスワードハッシュと稼働状態は含めない）
```

### オペレータ削除
```
1. ログイン済みオペレータが削除ボタンを押下
2. DELETE /api/operators/:id を呼び出し
3. 自分自身なら ForbiddenError（403）
4. 関連 sessions を削除したうえで operators を削除
```

---

## 6. 推定待ち時間フロー

### 現在の待ち時間
```
1. GET /api/wait-time（認証不要）
2. updated_at = now_jst() を1回生成し、以降の判定とレスポンスで使い回す
3. A = count_active()、W = count_waiting()、N = count_active_operators(updated_at)
4. L = A + W、C = N * P
5. N=0 なら estimated_wait_minutes=null、C>L なら 0、それ以外は切り上げ計算
```

### 時系列待ち時間
```
1. GET /api/wait-time/hourly（認証不要）
2. updated_at の前日 8:00〜18:00 を1時間刻みで11件生成する
3. 待ち時間は HOURLY_WAIT_TIME_MINUTES_BY_HOUR のモック値を返す
```

フロントエンドの `EndUserInquiry`（`/`）は入口フェーズ中、現在値を1分間隔で再取得し、時系列グラフは画面表示時に1回取得する。

---

## 7. サマリーボードフロー

```
1. オペレータが /operator/summary-board を開く（初期日付はブラウザのJST当日）
2. GET /api/summary?date=YYYY-MM-DD（認証必須）
3. SummaryRepository が選択日の問い合わせと最初のオペレータメッセージ時刻を取得
4. SummaryService が合計セッション数、平均初回応答秒、0〜23時の24件を算出
5. 未応答はセッション数に含め、平均初回応答からは除外する
6. 画面はKPIカードと棒グラフ・折れ線グラフで表示する
```
