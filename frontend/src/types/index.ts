// オペレータ
export interface Operator {
  id: number;
  username: string;
  display_name: string;
}

export const OPERATOR_AVAILABILITY_STATUS = {
  AWAY: 0,
  AVAILABLE: 1,
} as const;

export type OperatorAvailabilityStatus =
  typeof OPERATOR_AVAILABILITY_STATUS[keyof typeof OPERATOR_AVAILABILITY_STATUS];

export interface CurrentOperator extends Operator {
  availability_status: OperatorAvailabilityStatus;
}

// メッセージ
export interface Message {
  id: number;
  inquiry_id: number;
  sender_type: number; // 0:enduser, 1:operator, 2:system, 3:bot
  sender_name: string | null;
  content: string;
  created_at: string; // ISO 8601
}

// 問い合わせ
export interface Inquiry {
  id: number;
  status: number; // 0:waiting, 1:active, 2:closed, 3:bot
  assigned_operator_id: number | null;
  created_at: string;
  closed_at: string | null;
  bot_state: BotStateName | null;
}

// 表示用ステータス
export type DisplayStatus = 'waiting' | 'mine' | 'others' | 'closed' | 'bot';

// 表示用拡張型
export interface InquiryWithStatus extends Inquiry {
  display_status: DisplayStatus;
}

// ページングレスポンス
export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

// オペレータ作成レスポンス（パスワード付き）
export interface OperatorCreateResponse {
  operator: Operator;
  generated_password: string;
}

// 現在の待ち時間レスポンス
export interface WaitTimeResponse {
  estimated_wait_minutes: number | null;
  updated_at: string;
}

// 過去の待ち時間
export interface WaitTimeHistoryItem {
  time: string;
  estimated_wait_minutes: number;
}

// 待ち時間時系列レスポンス
export interface WaitTimeHistoryResponse {
  updated_at: string;
  items: WaitTimeHistoryItem[];
}

// 1時間ごとの問い合わせ集計
export interface HourlySummaryResponse {
  hour: number;
  session_count: number;
  average_first_response_seconds: number | null;
}

// 日次サマリーレスポンス
export interface DailySummaryResponse {
  date: string;
  total_sessions: number;
  average_first_response_seconds: number | null;
  hourly: HourlySummaryResponse[];
}

// === BOT事前質問 ===

// BOT質問状態（バックエンドの inquiries.bot_state と対応）
export type BotStateName =
  | 'INQUIRY_CATEGORY'
  | 'SIZE_QUESTION'
  | 'PRICE_RESOLUTION'
  | 'ADDITIONAL_QUESTION';

// 質問のUI種別
export type BotQuestionType = 'CHOICE' | 'SIZE';

// BOT処理の結果種別
export type BotResultType = 'QUESTION' | 'OPERATOR' | 'COMPLETED';

export interface BotOption {
  value: string;
  label: string;
}

export interface BotQuestion {
  message_id: number;
  state: BotStateName;
  type: BotQuestionType;
  text: string;
  options: BotOption[];
}

// BOT開始・回答で共通のレスポンス
export interface BotStepResponse {
  inquiry_id: number;
  result: BotResultType;
  messages: Message[];
  question: BotQuestion | null;
}

// === 事前ヒアリング管理 ===

// 事前ヒアリングの質問事項
// 「ボタン名」と「押下時にエンドユーザーへ案内する外部システムのURL」を一対一で対応させる
export interface PreHearingItem {
  id: number;
  label: string;
  // 外部システムを持たずBOT内で完結する項目はnull
  target_url: string | null;
  // コード（backend/app/bot/questions.py）で定義済みの項目は画面から削除できない
  is_builtin: boolean;
}

// 質問事項の追加入力
export interface PreHearingItemInput {
  label: string;
  target_url: string;
}

// BOTへ送る回答（CHOICEなら value、SIZEなら三辺を指定する）
export interface BotAnswerPayload {
  type: BotQuestionType;
  value?: string;
  length_cm?: number;
  width_cm?: number;
  height_cm?: number;
}
