# コンポーネント依存関係

## 依存関係マトリクス

### バックエンド依存関係

| コンポーネント | 依存先 | 依存タイプ |
|--------------|--------|-----------|
| auth_router | AuthService, OperatorService | 直接呼び出し |
| AuthService | AuthRepository | 直接呼び出し |
| AuthRepository | database | DB接続 |
| chat_router | BotService | 直接呼び出し |
| BotService | BotRepository, InquiryRepository, questions.py, ConnectionManager | 直接呼び出し |
| BotRepository | database | DB接続 |
| inquiry_router | InquiryService, InquiryRepository | 直接呼び出し |
| inquiry_router | AuthService | 認証ミドルウェア |
| InquiryService | InquiryRepository | 直接呼び出し |
| InquiryRepository | database | DB接続 |
| operator_router | OperatorService | 直接呼び出し |
| OperatorService | OperatorRepository | 直接呼び出し |
| OperatorRepository | database | DB接続 |
| wait_time_router | WaitTimeService | 直接呼び出し |
| WaitTimeService | InquiryRepository, AuthRepository | 直接呼び出し |
| summary_router | SummaryService | 直接呼び出し |
| SummaryService | SummaryRepository | 直接呼び出し |
| SummaryRepository | database | DB接続 |
| chat_ws | ChatService, AuthService, InquiryRepository | 直接呼び出し |
| ChatService | ChatRepository, InquiryRepository, ConnectionManager | 直接呼び出し |
| ChatRepository | database | DB接続 |

### フロントエンド依存関係

| コンポーネント | 依存先 | 依存タイプ |
|--------------|--------|-----------|
| OperatorLogin | AuthProvider | 認証状態管理 |
| InquiryList | AuthProvider | 認証情報参照 |
| InquiryDetail | AuthProvider, useChat | 認証情報参照、WebSocket通信 |
| EndUserInquiry | useBotChat, useChat, wait-time API | BOT REST・WebSocket・待ち時間取得 |
| SummaryBoard | AuthProvider, summary API | 認証必須の集計取得 |
| OperatorAdd / OperatorList | AuthProvider | 認証情報参照 |
| OperatorNav | AuthProvider | 稼働状態切替・ログアウト |
| AppShell | AuthProvider | 認証ガード |

---

## データフロー図

### エンドユーザのBOT + チャットフロー

```
+------------+    POST /api/chat/*    +-----------+     save      +--------+
| EndUser    | ---------------------> | chat_     | ----------->  | SQLite |
| Browser    | <--------------------- | router    |               |        |
+------------+    BotStepResponse     +-----------+               +--------+
      |
      | WebSocket（作成済み inquiry_id）
      v
+------------+                        +-----------+     save      +--------+
| EndUser    | ---------------------> | chat_ws   | ----------->  | SQLite |
| Browser    | <--------------------- |           | <-----------  |        |
+------------+     broadcast          +-----+-----+               +--------+
                                            |
                                            v
                                      +-----+-----+
                                      | Connection|
                                      | Manager   |
                                      +-----------+
```

### オペレータのチャットフロー

```
+------------+     WebSocket      +-----------+     save      +--------+
| Operator   | -----------------> | chat_ws   | ----------->  | SQLite |
| Browser    | <----------------- |    +      | <-----------  |        |
+------------+     broadcast      | auth check|     query     +--------+
                                  +-----+-----+
                                        |
                                        v
                                  +-----+-----+
                                  | Connection|
                                  | Manager   |
                                  +-----------+
```

### 問い合わせ担当取得フロー

```
+------------+      POST         +----------+     update    +--------+
| Operator   | ----------------> | inquiry  | ----------->  | SQLite |
| Browser    | <---------------- | _router  | <-----------  |        |
+------------+    response       +----+-----+    result     +--------+
                                      |
                                      v
                                 +----+-----+
                                 | Inquiry  |
                                 | Service  |
                                 | (排他    |
                                 |  制御)   |
                                 +----------+
```

### 認証・稼働状態フロー

```
+------------+   POST/PATCH      +----------+     query     +--------+
| Operator   | ----------------> | auth     | ----------->  | SQLite |
| Browser    | <---------------- | _router  | <-----------  |        |
+------------+  Set-Cookie /     +----+-----+    result     +--------+
                 CurrentOperator      |
                                      v
                                 +----+-----+
                                 | Auth /   |
                                 | Operator |
                                 | Service  |
                                 +----------+
```

### 待ち時間・サマリーフロー

```
EndUserInquiry  --GET /api/wait-time--> WaitTimeService
                                  ├ InquiryRepository.count_active/waiting
                                  └ AuthRepository.count_active_operators

SummaryBoard --GET /api/summary--> SummaryService --> SummaryRepository
```
