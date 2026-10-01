# コンポーネントメソッド

## バックエンド

### BE-001: 認証モジュール (auth)

#### Router (auth_router)
| メソッド | パス | 説明 |
|---------|------|------|
| `POST` | `/api/auth/login` | オペレータログイン。`CurrentOperatorResponse` を返す |
| `POST` | `/api/auth/logout` | オペレータログアウト |
| `GET` | `/api/auth/me` | ログイン中のオペレータ情報取得 |
| `PATCH` | `/api/auth/me/availability` | 本人の稼働状態更新 |

#### Service (AuthService)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `login(username, password)` | str, str | tuple[Operator, str] | 認証してセッション作成 |
| `logout(session_id)` | str | None | セッション破棄 |
| `get_current_operator(session_id)` | str \| None | Operator \| None | セッションからオペレータ取得 |

#### Repository (AuthRepository)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `find_operator_by_username(username)` | str | Operator \| None | ユーザー名でオペレータ検索 |
| `find_operator_by_id(operator_id)` | int | Operator \| None | IDでオペレータ検索 |
| `create_session(operator_id)` | int | str | セッション作成、session_id返却 |
| `get_session(session_id)` | str | Session \| None | セッション取得 |
| `delete_session(session_id)` | str | None | セッション削除 |
| `count_active_operators(updated_at)` | str | int | 稼働中かつ有効セッションの重複なし件数 |

---

### BE-002: 問い合わせ管理モジュール (inquiry)

#### Router (inquiry_router)
| メソッド | パス | 説明 |
|---------|------|------|
| `GET` | `/api/inquiries` | ページング付き一覧（レガシー） |
| `GET` | `/api/inquiries/open` | 未完了を優先順で全件取得 |
| `GET` | `/api/inquiries/closed` | 完了済みを最新50件取得 |
| `GET` | `/api/inquiries/:id` | 問い合わせ詳細取得 |
| `GET` | `/api/inquiries/:id/messages` | 問い合わせのメッセージ一覧取得 |
| `POST` | `/api/inquiries/:id/assign` | 問い合わせ担当取得 |

`/open` と `/closed` は `/{inquiry_id}` より前に定義する。

#### Service (InquiryService)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `list_inquiries(page, per_page, operator_id)` | int, int, int | PaginatedInquiryResponse | レガシー一覧 |
| `list_open(operator_id)` | int | list[InquiryResponse] | 未完了を優先順で返す |
| `list_closed()` | - | list[InquiryResponse] | 完了済みを上限件数まで返す |
| `get_inquiry(inquiry_id)` | int | Inquiry | 詳細取得 |
| `assign_operator(inquiry_id, operator_id)` | int, int | Inquiry | 担当割り当て（排他制御） |

#### Repository (InquiryRepository)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `find_open()` | - | list[Inquiry] | status != CLOSED を全件取得 |
| `find_recent_closed(limit)` | int | list[Inquiry] | 完了済みを SQL LIMIT で取得 |
| `find_all(page, per_page)` | int, int | list[Inquiry], int | ページング付き全件取得 |
| `find_by_id(inquiry_id)` | int | Inquiry \| None | ID検索 |
| `update_assignment(inquiry_id, operator_id)` | int, int | bool | 担当者更新（排他制御） |
| `update_status_closed(inquiry_id)` | int | bool | 終了更新。既終了なら False |
| `find_messages_by_inquiry_id(inquiry_id)` | int | list[Message] | メッセージを id 昇順で取得 |
| `count_waiting()` | - | int | WAITING かつ未割り当ての件数 |
| `count_active()` | - | int | ACTIVE の件数 |

---

### BE-003: チャットモジュール (chat)

#### WebSocket Handler (chat_ws)
| エンドポイント | 説明 |
|--------------|------|
| `ws://host/ws/chat/enduser/{inquiry_id}` | エンドユーザ用。作成済み inquiry_id のみ受付 |
| `ws://host/ws/chat/operator/{inquiry_id}` | オペレータ用。担当者のみ接続可 |

#### Service (ChatService)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `send_message(inquiry_id, sender_type, content, ...)` | int, int, str | dict \| None | 保存・ブロードキャスト。拒否時は None |
| `close_inquiry(inquiry_id)` | int | None | 終了処理。既終了なら何もしない |

#### Repository (ChatRepository)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `save_message(...)` | inquiry_id, sender_type, ... | Message | メッセージ保存 |
| `find_by_inquiry_id(inquiry_id)` | int | list[Message] | 問い合わせIDで検索 |

---

### BE-004: WebSocket接続管理 (connection_manager)

| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `connect(websocket, inquiry_id, user_type)` | WebSocket, int, str | None | 接続登録（accept含む） |
| `disconnect(websocket, inquiry_id)` | WebSocket, int | None | 接続解除 |
| `broadcast(inquiry_id, message)` | int, dict | None | 問い合わせグループへブロードキャスト |
| `update_activity(websocket, inquiry_id)` | WebSocket, int | None | 最終アクティビティ更新 |
| `get_timed_out_inquiries(timeout_seconds)` | int | list[int] | タイムアウトした問い合わせID |
| `get_connections(inquiry_id)` | int | list[ConnectionInfo] | 問い合わせの接続一覧 |

---

### BE-006: オペレータ管理モジュール (operator)

#### Router (operator_router)
| メソッド | パス | 説明 |
|---------|------|------|
| `GET` | `/api/operators` | 一覧取得 |
| `POST` | `/api/operators` | 追加（パスワード自動発行） |
| `DELETE` | `/api/operators/:id` | 削除 |

#### Service (OperatorService)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `list_operators()` | - | list[Operator] | 全件取得 |
| `create_operator(username, display_name)` | str, str | tuple[Operator, str] | 作成と平文パスワード |
| `update_availability(operator_id, availability_status)` | int, int | Operator | 稼働状態更新 |
| `delete_operator(target_id, current_operator_id)` | int, int | None | 自己削除禁止 |

#### Repository (OperatorRepository)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `find_all()` | - | list[Operator] | 全件取得 |
| `find_by_username(username)` | str | Operator \| None | ユーザー名検索 |
| `create(username, password_hash, display_name)` | str, str, str | Operator | 作成 |
| `update_availability(operator_id, availability_status)` | int, int | Operator | 状態更新 |
| `delete(operator_id)` | int | None | セッションごと削除 |

---

### BE-007: BOT事前質問モジュール (bot)

#### Router (chat_router)
| メソッド | パス | 説明 |
|---------|------|------|
| `POST` | `/api/chat/start` | BOT開始。201 で BotStepResponse |
| `POST` | `/api/chat/{inquiry_id}/bot/answer` | BOT回答 |

#### Service (BotService)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `start()` | - | BotStepResult | 問い合わせ作成と最初の質問 |
| `answer(inquiry_id, state, payload)` | int, str, BotAnswerPayload | BotStepResult | 回答保存と遷移 |

#### Repository (BotRepository)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `create_bot_inquiry(question_text)` | str | tuple[Inquiry, Message] | BOT問い合わせ作成 |
| `save_answer_and_transition(...)` | inquiry_id, answer_text, next_status, ... | tuple[Message, Message \| None] | 回答・次質問・状態更新を1トランザクションで実行 |

---

### BE-008: 待ち時間モジュール (wait_time)

#### Router (wait_time_router)
| メソッド | パス | 説明 |
|---------|------|------|
| `GET` | `/api/wait-time` | 現在の推定待ち時間 |
| `GET` | `/api/wait-time/hourly` | 前日8:00〜18:00のモック時系列 |

#### Service (WaitTimeService)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `get_current_wait_time()` | - | WaitTimeResponse | A, W, N から案Bで算出 |
| `get_hourly_wait_times()` | - | HourlyWaitTimeResponse | 設定値から11件生成 |

---

### BE-009: サマリーモジュール (summary)

#### Router (summary_router)
| メソッド | パス | 説明 |
|---------|------|------|
| `GET` | `/api/summary?date=` | 指定日の日次集計 |

#### Service (SummaryService)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `get_daily_summary(selected_date)` | date | DailySummaryResponse | KPIと24時間分の時間帯 |

#### Repository (SummaryRepository)
| メソッド | 入力 | 出力 | 説明 |
|---------|------|------|------|
| `find_inquiries_with_first_response(selected_date)` | date | list[InquiryFirstResponse] | 選択日の問い合わせと初回オペレータ応答 |

---

## フロントエンド

### FE-005: 認証コンテキスト (AuthProvider)

| メソッド/状態 | 型 | 説明 |
|-------------|------|------|
| `operator` | CurrentOperator \| null | ログイン中のオペレータ情報（稼働状態を含む） |
| `isAuthenticated` | boolean | 認証状態 |
| `isLoading` | boolean | 起動時のセッション確認中 |
| `login(username, password)` | Promise\<void\> | ログイン処理 |
| `logout()` | Promise\<void\> | ログアウト処理 |
| `updateAvailability(status)` | Promise\<void\> | 稼働状態更新 |

### WebSocket フック (useChat)

| メソッド/状態 | 型 | 説明 |
|-------------|------|------|
| `messages` | Message[] | WebSocketで受信したメッセージ |
| `sendMessage(content)` | (string) => void | メッセージ送信 |
| `isConnected` | boolean | WebSocket接続状態 |
| `connect(inquiryId, userType)` | (number, 'enduser' \| 'operator') => void | 作成済み inquiry_id で接続 |
| `disconnect()` | () => void | 終了メッセージ送信後に切断 |

### BOT フック (useBotChat)

| メソッド/状態 | 型 | 説明 |
|-------------|------|------|
| `inquiryId` | number \| null | BOT開始で作成された問い合わせID |
| `phase` | STARTING \| BOT \| OPERATOR \| COMPLETED \| ERROR | 進行状況 |
| `messages` | Message[] | BOT REST で得たメッセージ |
| `question` | BotQuestion \| null | 現在の質問 |
| `isSubmitting` | boolean | 回答送信中 |
| `start()` | () => Promise\<void\> | POST /api/chat/start |
| `answer(payload)` | (BotAnswerPayload) => Promise\<void\> | POST /api/chat/{id}/bot/answer |
