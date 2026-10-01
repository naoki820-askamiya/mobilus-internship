# BOT事前質問機能 フロントエンド仕様書

## 1. 責務

バックエンドから返された現在のBOT質問を適切なUIで表示し、回答を送信する。  
質問の分岐はフロントエンドで判断しない。

---

## 2. 画面フロー

```text
1. BOT開始処理を実行
2. Inquiry IDと最初の質問を取得
3. Inquiry IDでWebSocketへ接続
4. BOT質問と回答UIを表示
5. 回答結果に応じて次質問・通常チャット・終了へ遷移
```

既存の`inquiry_id=0`によるWebSocket接続は行わない。

---

## 3. 画面下部の切り替え

```text
BOT対応中:
    BotQuestionInputを表示
    MessageInputを非表示

オペレーター対応中:
    BotQuestionInputを非表示
    MessageInputを表示

終了後:
    両方を非表示
```

BOT中は通常チャットを入力できないようにする。バックエンドでも通常メッセージは拒否する。

---

## 4. 質問データ

```typescript
type BotState =
  | 'INQUIRY_CATEGORY'
  | 'SIZE_QUESTION'
  | 'PRICE_RESOLUTION'
  | 'ADDITIONAL_QUESTION';

type QuestionType = 'CHOICE' | 'SIZE';

interface BotQuestion {
  message_id: number;
  state: BotState;
  type: QuestionType;
  text: string;
  options: Array<{
    value: string;
    label: string;
  }>;
}
```

質問文、選択肢、表示順はAPIレスポンスを利用し、フロントエンドへ固定しない。

---

## 5. 質問形式別UI

質問形式は`CHOICE`と`SIZE`の2種類に統一する。

`text`はBOTメッセージとしてチャット吹き出しに表示されるため、回答UIでは重複表示せず`options`と入力欄だけを描画する。

### CHOICE

`options`をボタン表示する。問い合わせ内容・解決確認・他に質問有無・料金結果後の確認は、すべてこのUIを使う。

```text
options:
    [料金] [その他]
    または
    [はい] [いいえ]
```

料金結果の表示も、別UIではなく`text`に含めて返す。

### SIZE

三辺入力欄と、APIから返された補助選択肢を表示する。

```text
入力欄（cm）:
    - 縦
    - 横
    - 高さ

補助選択肢:
    - サイズの測り方がわからない
    - サイズに関係ない
```

各入力値は0より大きい数値を必須とする。

---

## 6. 選択肢と回答後の表示

回答UIは、現在回答可能な最新のBOT質問にだけ表示する。

```text
回答前:
    BOT「問い合わせ内容を選択してください」
    [料金] [その他]

回答後:
    BOT「問い合わせ内容を選択してください」
    USER「料金」
```

回答時の処理：

```text
1. 選択・送信後、回答UIを無効化
2. API成功後、回答済み質問のボタンを削除
3. 保存済みユーザ回答を通常メッセージとして追加
4. 次質問があれば、その質問にだけ回答UIを表示
5. API失敗時は回答UIを再度有効化
```

過去のBOT質問には回答UIを再表示しない。

現在の質問は`currentQuestion.message_id`で識別し、`sender_type=BOT`だけを条件にボタンを表示しない。

---

## 7. 回答結果

いずれの結果でも、レスポンスの`messages`をそのままメッセージ一覧へ追加する。

### QUESTION

```text
1. messages（ユーザ回答 + BOT質問）をメッセージ一覧へ追加
2. question.typeに対応する回答UIを表示
```

### OPERATOR

```text
1. BOT回答UIを削除
2. WebSocket接続を確認
3. 通常のMessageInputを表示
4. 既存チャット処理へ切り替え
```

### COMPLETED

```text
1. すべての入力UIを削除
2. 終了表示へ切り替え
3. WebSocketを切断
```

---

## 8. メッセージ表示

BOT質問、ユーザ回答、料金結果、通常チャットを既存の`ChatWindow`へ時系列で表示する。

```typescript
export const SENDER_TYPE = {
  ENDUSER: 0,
  OPERATOR: 1,
  SYSTEM: 2,
  BOT: 3,
} as const;
```

1. `MessageBubble`へBOT用表示を追加し、ユーザ・オペレーター・システムメッセージと区別する。

BOT質問はHTTPレスポンスから追加し、WebSocketから重複追加しない。ユーザ回答もAPIから返された保存済みMessageを追加する。

---

## 9. コンポーネント

質問UIは`CHOICE`と`SIZE`の2種類だけとし、選択式の質問はすべて`ChoiceQuestion`で表示する。押下後の遷移（次質問・オペレーター・終了）はコンポーネント内で分岐せず、`BotConversation`がAPI結果で処理する。

### 構成

BOT会話の状態管理はコンポーネントではなく`useBotChat`フックへ切り出し、`EndUserInquiry`が既存の`useChat`と組み合わせる。

```text
EndUserInquiry                  … 待ち時間確認 + useBotChat + useChat
├─ ChatWindow
│  └─ MessageBubble
├─ BotQuestionInput             … 現在の質問への回答UI（BOT中のみ）
│  ├─ ChoiceQuestion           … type=CHOICE のとき
│  └─ SizeQuestion             … type=SIZE のとき
└─ MessageInput                 … オペレーター対応中のみ
```

### 追加フック

#### `useBotChat`

- BOT開始、回答API送信、現在質問と進行状況（`phase`）の保持
- `QUESTION` / `OPERATOR` / `COMPLETED` の結果を`phase`へ反映
- BOTのメッセージ一覧を保持し、`EndUserInquiry`がWebSocket受信分と連結する

### 追加コンポーネント

#### `BotQuestionInput`

- 現在の`BotQuestion`を受け取り、`type`に応じて子コンポーネントを出し分ける薄いラッパー
- 質問の出し分けロジックは持たない（APIが返した`type`をそのまま使う）

```text
type === 'CHOICE' → ChoiceQuestion
type === 'SIZE'   → SizeQuestion
```

#### `ChoiceQuestion`

選択式の質問はすべてこの1コンポーネントで表示する。


| 用途        | `bot_state`           | 表示例                    |
| --------- | --------------------- | ---------------------- |
| 問い合わせ内容   | `INQUIRY_CATEGORY`    | text + [料金] [その他]      |
| 料金結果・解決確認 | `PRICE_RESOLUTION`    | text（料金込み）+ [はい] [いいえ] |
| 他に質問有無    | `ADDITIONAL_QUESTION` | text + [はい] [いいえ]      |


責務：

```text
- optionsをボタン表示
- 押下時に onSelect(value) を呼ぶ
- 送信中は disabled
```

「終了」「オペレーター接続」などの分岐は持たない。

#### `SizeQuestion`

サイズ入力が必要な質問専用。


| 用途    | `bot_state`     | 表示                |
| ----- | --------------- | ----------------- |
| サイズ入力 | `SIZE_QUESTION` | 縦・横・高さ（cm）+ 補助ボタン |


責務：

```text
- 三辺の入力欄を表示
- 補助選択肢（測り方わからない / サイズに関係ない）を表示
- 入力送信時に onSubmitSize({ length_cm, width_cm, height_cm }) を呼ぶ
- 補助ボタン押下時に onSelect(value) を呼ぶ
```

### 変更コンポーネント

```text
EndUserInquiry
    useBotChatの開始・phaseに応じた画面下部の切り替え

MessageBubble
    BOTメッセージ表示と、改行を含む文言の表示を追加

useChat
    作成済みInquiry IDでWebSocket接続
```

---

## 10. エラー・二重送信

- 回答中はボタンと入力欄を無効化する
- 回答失敗時は入力内容を保持して再送可能にする
- 状態不一致時は最新状態と履歴を再取得する
- `message_id`でメッセージの重複表示を防ぐ
- WebSocket切断中は回答・通常メッセージ送信を無効化する

