# シーケンス図

## 1. オペレータログイン

```mermaid
sequenceDiagram
    actor OP as オペレータ
    participant FE as OperatorLogin
    participant AR as auth_router
    participant AS as AuthService
    participant AREP as AuthRepository
    participant DB as SQLite

    OP->>FE: ユーザー名・パスワード入力
    FE->>AR: POST /api/auth/login
    AR->>AS: login(username, password)
    AS->>AREP: find_operator_by_username(username)
    AREP->>DB: SELECT * FROM operators WHERE username = ?
    DB-->>AREP: Operator or None
    alt オペレータ未存在
        AREP-->>AS: None
        AS-->>AR: 認証失敗エラー
        AR-->>FE: 401 Unauthorized
        FE-->>OP: エラーメッセージ表示
    else パスワード不一致
        AS->>AS: bcrypt.verify(password, hash)
        AS-->>AR: 認証失敗エラー
        AR-->>FE: 401 Unauthorized
        FE-->>OP: エラーメッセージ表示
    else 認証成功
        AS->>AS: bcrypt.verify(password, hash) = True
        AS->>AREP: create_session(operator_id)
        AREP->>AREP: session_id = uuid4()
        AREP->>DB: INSERT INTO sessions (id, operator_id, expires_at)
        DB-->>AREP: OK
        AREP-->>AS: session_id
        AS-->>AR: Operator（availability_status含む）
        AR-->>FE: 200 OK + Set-Cookie: session_id
        FE->>FE: AuthContext更新
        FE-->>OP: 問い合わせ一覧に遷移
    end
```

## 2. 問い合わせ一覧取得（未完了 + 完了済み）

```mermaid
sequenceDiagram
    actor OP as オペレータ
    participant FE as InquiryList
    participant IR as inquiry_router
    participant IS as InquiryService
    participant IREP as InquiryRepository
    participant DB as SQLite

    OP->>FE: 問い合わせ一覧画面表示
    par 未完了
        FE->>IR: GET /api/inquiries/open
        IR->>IS: list_open(operator_id)
        IS->>IREP: find_open()
        IREP->>DB: SELECT * FROM inquiries WHERE status != CLOSED
        IREP-->>IS: inquiries
        IS->>IS: display_status算出と優先順ソート
        IS-->>FE: 200 OK [mine, waiting, bot, others]
    and 完了済み
        FE->>IR: GET /api/inquiries/closed
        IR->>IS: list_closed()
        IS->>IREP: find_recent_closed(50)
        IREP->>DB: SELECT * FROM inquiries WHERE status=CLOSED ORDER BY closed_at DESC LIMIT 50
        IS-->>FE: 200 OK [closed]
    end
    FE->>FE: 未完了の後ろに完了済みを結合
    FE-->>OP: 一覧表示（ステータスバッジ付き）
```

## 3. 問い合わせ担当取得（排他制御）

```mermaid
sequenceDiagram
    actor OP as オペレータ
    participant FE as InquiryList
    participant IR as inquiry_router
    participant IS as InquiryService
    participant IREP as InquiryRepository
    participant DB as SQLite

    OP->>FE: 「担当する」ボタン押下
    FE->>IR: POST /api/inquiries/5/assign
    IR->>IS: assign_operator(inquiry_id=5, operator_id=1)
    IS->>IREP: update_assignment(inquiry_id=5, operator_id=1)
    IREP->>DB: UPDATE inquiries SET assigned_operator_id=1, status=1<br/>WHERE id=5 AND assigned_operator_id IS NULL AND status=0
    alt 更新成功（affected_rows = 1）
        DB-->>IREP: OK (1 row affected)
        IREP-->>IS: True
        IS-->>IR: 更新されたInquiry
        IR-->>FE: 200 OK
        FE-->>OP: ステータス「自分の担当」に更新
    else 排他制御失敗（他のオペレータが先に取得 / BOT中 / 終了済み）
        DB-->>IREP: OK (0 rows affected)
        IREP-->>IS: False
        IS-->>IR: ConflictError
        IR-->>FE: 409 Conflict
        FE-->>OP: エラーメッセージ表示
    end
```

## 4. BOT事前質問の開始

```mermaid
sequenceDiagram
    actor EU as エンドユーザ
    participant FE as EndUserInquiry
    participant CR as chat_router
    participant BS as BotService
    participant BREP as BotRepository
    participant CW as chat_ws
    participant CM as ConnectionManager
    participant DB as SQLite

    EU->>FE: ページアクセス (/)
    FE->>CR: POST /api/chat/start
    CR->>BS: start()
    BS->>BREP: create_bot_inquiry(最初の質問文)
    BREP->>DB: INSERT inquiries (status=BOT, bot_state=INQUIRY_CATEGORY)
    BREP->>DB: INSERT messages (sender_type=BOT)
    BREP-->>BS: Inquiry, Message
    BS-->>FE: 201 {inquiry_id, result:QUESTION, messages, question}
    FE->>CW: WebSocket接続 /ws/chat/enduser/{inquiry_id}
    CW->>CM: connect(enduser)
    CW-->>FE: connected
    FE-->>EU: 最初のBOT質問と選択肢を表示
```

## 5. BOT回答とオペレータ対応への移行

```mermaid
sequenceDiagram
    actor EU as エンドユーザ
    participant FE as EndUserInquiry
    participant CR as chat_router
    participant BS as BotService
    participant BREP as BotRepository
    participant DB as SQLite

    EU->>FE: 「その他」を選択
    FE->>CR: POST /api/chat/{id}/bot/answer
    CR->>BS: answer(inquiry_id, state, payload)
    BS->>BS: status=BOT かつ bot_state 一致を確認
    BS->>BREP: save_answer_and_transition
    BREP->>DB: INSERT ユーザ回答
    BREP->>DB: INSERT 「オペレーターにおつなぎします...」
    BREP->>DB: UPDATE status=WAITING, bot_state=NULL
    BS-->>FE: {result:OPERATOR, messages, question:null}
    FE->>FE: BotQuestionInput を隠し MessageInput を表示
    FE-->>EU: 通常チャット入力が可能
```

## 6. メッセージ送受信（オペレータ対応中）

```mermaid
sequenceDiagram
    actor EU as エンドユーザ
    participant FE_EU as EndUserInquiry
    participant CW as chat_ws
    participant CS as ChatService
    participant CREP as ChatRepository
    participant CM as ConnectionManager
    participant FE_OP as InquiryDetail
    actor OP as オペレータ
    participant DB as SQLite

    EU->>FE_EU: メッセージ入力・送信
    FE_EU->>CW: WebSocket: {type: message, content: "こんにちは"}
    CW->>CS: send_message(inquiry_id, ENDUSER, content)
    CS->>CS: CLOSED / BOT なら拒否
    CS->>CREP: save_message(Message)
    CREP->>DB: INSERT INTO messages
    CS->>CM: broadcast(inquiry_id, message)
    CM-->>FE_EU: WebSocket: Message
    CM-->>FE_OP: WebSocket: Message
    FE_EU-->>EU: メッセージ表示（右側）
    FE_OP-->>OP: メッセージ表示（左側）

    OP->>FE_OP: 返信メッセージ入力・送信
    FE_OP->>CW: WebSocket: {type: message, content: "お問い合わせありがとうございます"}
    CW->>CS: send_message(inquiry_id, OPERATOR, content)
    CS->>CS: 権限確認（assigned_operator_id == operator_id）
    CS->>CREP: save_message(Message)
    CS->>CM: broadcast(inquiry_id, message)
    CM-->>FE_OP: WebSocket: Message
    CM-->>FE_EU: WebSocket: Message
    FE_OP-->>OP: メッセージ表示（右側）
    FE_EU-->>EU: メッセージ表示（左側）
```

## 7. セッション終了（明示的な終了ボタン）

```mermaid
sequenceDiagram
    actor EU as エンドユーザ
    participant FE_EU as EndUserInquiry
    participant CW as chat_ws
    participant CS as ChatService
    participant IREP as InquiryRepository
    participant CREP as ChatRepository
    participant CM as ConnectionManager
    participant FE_OP as InquiryDetail
    actor OP as オペレータ
    participant DB as SQLite

    EU->>FE_EU: 「終了」ボタン押下
    FE_EU->>CW: WebSocket: {type: close}
    CW->>CS: close_inquiry(inquiry_id)
    CS->>IREP: update_status_closed(inquiry_id)
    IREP->>DB: UPDATE status=CLOSED, bot_state=NULL, closed_at=now
    alt 既に終了済み
        IREP-->>CS: False
        Note over CS: 何もしない
    else 今回終了
        CS->>CREP: save_message(system_message)
        CREP->>DB: INSERT sender_type=SYSTEM 「ユーザーが退出しました」
        CS->>CM: broadcast(message)
        CS->>CM: broadcast({type: closed})
        CM-->>FE_OP: システムメッセージ + closed
        FE_OP-->>OP: 送信無効化
        CM-->>FE_EU: closed
        FE_EU-->>EU: 「チャットが終了しました」
    end
```

## 8. セッションタイムアウト

```mermaid
sequenceDiagram
    participant CM as ConnectionManager
    participant CS as ChatService
    participant IREP as InquiryRepository
    participant CREP as ChatRepository
    participant FE_EU as EndUserInquiry
    participant FE_OP as InquiryDetail
    participant DB as SQLite

    Note over CM: エンドユーザ接続の最終アクティビティを保持
    CM->>CM: get_timed_out_inquiries(TIMEOUT_SECONDS)
    CM-->>CS: timeout_connections = [inquiry_id]
    CS->>IREP: update_status_closed(inquiry_id)
    IREP->>DB: UPDATE status=CLOSED, closed_at=now
    CS->>CREP: save_message(system_message)
    CS->>CM: broadcast(system_message / closed)
    CM-->>FE_OP: 送信無効化
    CM-->>FE_EU: 送信無効化
```

## 9. オペレータ ログアウト

```mermaid
sequenceDiagram
    actor OP as オペレータ
    participant FE as OperatorNav
    participant AR as auth_router
    participant AS as AuthService
    participant AREP as AuthRepository
    participant DB as SQLite

    OP->>FE: ログアウトボタン押下
    FE->>AR: POST /api/auth/logout
    AR->>AS: logout(session_id)
    AS->>AREP: delete_session(session_id)
    AREP->>DB: DELETE FROM sessions WHERE id = ?
    DB-->>AREP: OK
    AREP-->>AS: OK
    AS-->>AR: OK
    AR-->>FE: 200 OK + Set-Cookie: clear
    FE->>FE: AuthContext クリア
    FE-->>OP: ログイン画面に遷移
```

## 10. オペレータ稼働状態の更新

```mermaid
sequenceDiagram
    actor OP as オペレータ
    participant FE as OperatorNav
    participant AR as auth_router
    participant OS as OperatorService
    participant OREP as OperatorRepository
    participant DB as SQLite

    OP->>FE: 「稼働にする」または「離席にする」押下
    FE->>AR: PATCH /api/auth/me/availability {availability_status}
    AR->>OS: update_availability(operator_id, status)
    OS->>OREP: update_availability(operator_id, status)
    OREP->>DB: UPDATE operators SET availability_status=?
    OREP-->>OS: Operator
    OS-->>AR: Operator
    AR-->>FE: 200 CurrentOperator
    FE->>FE: AuthContext の operator を置き換え
    FE-->>OP: 状態表示とボタン文言を更新
```

## 11. オペレータ追加

```mermaid
sequenceDiagram
    actor OP as オペレータ
    participant FE as OperatorAdd
    participant OR as operator_router
    participant OS as OperatorService
    participant OREP as OperatorRepository
    participant DB as SQLite

    OP->>FE: username, display_name 入力
    FE->>OR: POST /api/operators {username, display_name}
    OR->>OS: create_operator(username, display_name)
    OS->>OREP: find_by_username(username)
    OREP->>DB: SELECT * FROM operators WHERE username = ?
    DB-->>OREP: result
    alt username 重複あり
        OREP-->>OS: Operator (既存)
        OS-->>OR: ConflictError
        OR-->>FE: 409 Conflict
        FE-->>OP: 「このユーザー名は既に使用されています」
    else username 利用可能
        OREP-->>OS: None
        OS->>OS: password = secrets.token (英数字12文字)
        OS->>OS: password_hash = bcrypt.hash(password)
        OS->>OREP: create(Operator{username, password_hash, display_name})
        OREP->>DB: INSERT INTO operators（availability_status DEFAULT 0）
        DB-->>OREP: OK
        OREP-->>OS: Operator
        OS-->>OR: {operator, password}
        OR-->>FE: 201 Created {operator, generated_password}
        FE-->>OP: パスワード表示（コピー可能）
    end
```

## 12. オペレータ削除

```mermaid
sequenceDiagram
    actor OP as オペレータ
    participant FE as OperatorList
    participant OR as operator_router
    participant OS as OperatorService
    participant OREP as OperatorRepository
    participant DB as SQLite

    OP->>FE: 削除ボタン押下（target_id=3）
    FE->>OR: DELETE /api/operators/3
    OR->>OS: delete_operator(target_id=3, current_operator_id=1)
    alt 自分自身を削除しようとした場合
        OS-->>OR: ForbiddenError
        OR-->>FE: 403 Forbidden
        FE-->>OP: エラーメッセージ
    else 他のオペレータを削除
        OS->>OREP: delete(target_id=3)
        OREP->>DB: DELETE FROM sessions WHERE operator_id = 3
        DB-->>OREP: OK
        OREP->>DB: DELETE FROM operators WHERE id = 3
        DB-->>OREP: OK
        OREP-->>OS: OK
        OS-->>OR: OK
        OR-->>FE: 204 No Content
        FE-->>OP: 一覧更新
    end
```

## 13. 推定待ち時間の取得

```mermaid
sequenceDiagram
    actor EU as エンドユーザ
    participant FE as EndUserInquiry
    participant WR as wait_time_router
    participant WS as WaitTimeService
    participant IREP as InquiryRepository
    participant AREP as AuthRepository
    participant DB as SQLite

    EU->>FE: / を開く（待ち時間確認）
    FE->>WR: GET /api/wait-time
    WR->>WS: get_current_wait_time()
    WS->>WS: updated_at = now_jst()
    WS->>IREP: count_active() / count_waiting()
    WS->>AREP: count_active_operators(updated_at)
    AREP->>DB: 有効セッションかつ AVAILABLE の重複なし件数
    WS->>WS: L=A+W, C=N*P から切り上げ計算
    WS-->>FE: {estimated_wait_minutes, updated_at}
    FE->>WR: GET /api/wait-time/hourly
    WR->>WS: get_hourly_wait_times()
    WS-->>FE: 前日8:00〜18:00のモック11件
    FE-->>EU: 現在の待ち時間と時系列グラフ
```

## 14. サマリーボード

```mermaid
sequenceDiagram
    actor OP as オペレータ
    participant FE as SummaryBoard
    participant SR as summary_router
    participant SS as SummaryService
    participant SREP as SummaryRepository
    participant DB as SQLite

    OP->>FE: /operator/summary-board を開く（初期日付=JST当日）
    FE->>SR: GET /api/summary?date=2026-08-19
    SR->>SS: get_daily_summary(date)
    SS->>SREP: find_inquiries_with_first_response(date)
    SREP->>DB: 選択日の問い合わせと最初のオペレータメッセージ
    SS->>SS: 合計件数・平均秒・0〜23時を算出
    SS-->>FE: DailySummaryResponse
    FE-->>OP: KPIとグラフを表示
```
