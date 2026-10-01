# BOT事前質問機能 バックエンド仕様書

## 1. 責務

BOT質問の開始、回答保存、状態遷移、料金計算、通常チャットへの切り替えを管理する。  
質問フローはバックエンドを正とする。

---

## 2. データ・型変更

```text
InquiryStatus.BOT = 3

BotState:
    INQUIRY_CATEGORY
    SIZE_QUESTION
    PRICE_RESOLUTION
    ADDITIONAL_QUESTION

SenderType.BOT = 3
```

`inquiries`に以下を追加する。

```sql
bot_state TEXT NULL
```

- `status=BOT`の間だけ`bot_state`へ現在状態を保存する
- オペレーター移行・終了時は`bot_state=NULL`にする
- `messages`のスキーマは変更しない

---

## 3. 質問定義とDB保存

質問文、質問形式、選択肢、遷移条件はバックエンドのコードで管理し、DBには保存しない。

DBへ保存するもの：

```text
BOT質問・料金結果:
    sender_type = BOT
    content = 実際に表示した文言

ユーザ回答:
    sender_type = ENDUSER
    content = 選択した文言または入力したサイズ
```

選択肢の個数は質問定義内のリストで表現する。

---

## 4. BOT開始

```http
POST /api/chat/start
```

処理：

```text
1. status=BOT、bot_state=INQUIRY_CATEGORYでInquiryを作成
2. 最初のBOT質問をmessagesへ保存
3. Inquiry IDと保存済み質問を返却
```

レスポンス例：

```json
{
  "inquiry_id": 1,
  "result": "QUESTION",
  "messages": [
    {
      "id": 1,
      "inquiry_id": 1,
      "sender_type": 3,
      "sender_name": null,
      "content": "お問い合わせ内容を選択してください。",
      "created_at": "2026-08-18 17:00:00"
    }
  ],
  "question": {
    "message_id": 1,
    "state": "INQUIRY_CATEGORY",
    "type": "CHOICE",
    "text": "お問い合わせ内容を選択してください。",
    "options": [
      { "value": "PRICE", "label": "料金" },
      { "value": "OTHER", "label": "その他" }
    ]
  }
}
```

`messages`は今回追加されたメッセージを時系列順に並べたもので、フロントはこれをそのままチャット履歴へ追加する。

既存の「初回チャットメッセージ送信時のInquiry作成」は使用しない。

---

## 5. BOT回答

全質問を1つのエンドポイントで処理する。

```http
POST /api/chat/{inquiry_id}/bot/answer
```

リクエスト例：

```json
{
  "state": "INQUIRY_CATEGORY",
  "answer": {
    "type": "CHOICE",
    "value": "PRICE"
  }
}
```

処理：

```text
1. Inquiryがstatus=BOTであることを確認
2. DBのbot_stateとリクエストのstateが一致することを確認
3. 回答形式と値を検証
4. ユーザ回答をmessagesへ保存
5. 次状態を決定
6. 次質問があればmessagesへ保存
7. statusとbot_stateを更新
8. QUESTION / OPERATOR / COMPLETEDを返却
```

回答保存、次質問保存、Inquiry更新は同一トランザクションで行う。

レスポンスは開始APIと同じ形式で、`messages`に「ユーザ回答」と「BOT応答」を時系列順に含める。

```json
{
  "inquiry_id": 1,
  "result": "QUESTION",
  "messages": [{ "sender_type": 0 }, { "sender_type": 3 }],
  "question": {}
}
```

`OPERATOR`では以下へ更新し、`question`は`null`にする。

```text
status: BOT → WAITING
bot_state: NULL
BOTメッセージ: 「オペレーターにおつなぎします。少々お待ちください。」
```

`COMPLETED`では既存の終了処理を実行し、`bot_state=NULL`にする。  
終了を伝えるBOTメッセージを保存したうえで、WebSocketへ`closed`を通知する。

---

## 6. 状態遷移

```text
INQUIRY_CATEGORY
├─ PRICE → SIZE_QUESTION
└─ OTHER → OPERATOR

SIZE_QUESTION
├─ サイズ入力 → 料金計算 → PRICE_RESOLUTION
├─ UNKNOWN_MEASUREMENT → OPERATOR
└─ UNRELATED → OPERATOR

PRICE_RESOLUTION
├─ RESOLVED → ADDITIONAL_QUESTION
└─ UNRESOLVED → OPERATOR

ADDITIONAL_QUESTION
├─ HAS_MORE → INQUIRY_CATEGORY
└─ NO_MORE → COMPLETED
```

---

## 7. 料金計算

縦・横・高さをセンチメートル単位で受け取る。  
各値は0より大きい数値を必須とし、不正な場合は`SIZE_QUESTION`のまま再入力を求める。

```text
三辺合計 = 縦 + 横 + 高さ

150cm以下              → 250円
150cm超、200cm以下     → 500円
200cm超、250cm以下     → 1,000円
250cm超                → 1,500円
```

境界値と料金は定数として管理する。

保存するユーザ回答例：

```text
縦100cm、横30cm、高さ20cm
```

保存・返却するBOTメッセージ例：

```text
三辺の合計は150cmです。
料金は250円です。解決しましたか？
```

料金結果と解決確認は1つのBOT質問として扱う。

---

## 8. 通常チャット・WebSocket

BOT開始後、作成済みInquiry IDでエンドユーザのWebSocketを接続する。  
BOT中は切断検知に利用し、BOT質問はHTTPレスポンスで返してWebSocketでは重複配信しない。

通常メッセージ送信時はDBのInquiryを確認する。

```text
status == BOT または bot_state != NULL
    → 保存せず拒否

status == WAITING かつ bot_state == NULL
    → 通常チャットを許可
```

---

## 9. 既存機能への変更

- `status=BOT`は問い合わせ一覧で「BOT対応中」と表示する
- BOT中は担当取得・オペレーターのチャット参加を拒否する
- `WAITING`へ移行後に担当取得を許可する
- BOT質問と回答を既存のメッセージ履歴へ含める
- `NO_MORE`を問い合わせ終了条件へ追加する
- 終了処理の二重実行を防止する

---

## 10. エラー

```text
Inquiryなし                         → 404
statusがBOTではない                 → 409
DBとリクエストのstateが不一致       → 409
回答形式・値が不正                  → 422
BOT中の通常メッセージ               → 保存せず拒否
```

