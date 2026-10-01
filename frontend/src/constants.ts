import { PreHearingItem } from './types';

// 問い合わせステータスコード
export const INQUIRY_STATUS = {
  WAITING: 0,
  ACTIVE: 1,
  CLOSED: 2,
  BOT: 3,
} as const;

// メッセージ送信者タイプコード
export const SENDER_TYPE = {
  ENDUSER: 0,
  OPERATOR: 1,
  SYSTEM: 2,
  BOT: 3,
} as const;

// BOT質問のUI種別
export const BOT_QUESTION_TYPE = {
  CHOICE: 'CHOICE',
  SIZE: 'SIZE',
} as const;

// BOT処理の結果種別
export const BOT_RESULT = {
  QUESTION: 'QUESTION',
  OPERATOR: 'OPERATOR',
  COMPLETED: 'COMPLETED',
} as const;

// サイズ入力の許容範囲（cm）: バックエンドの検証値と揃える
export const SIZE_MIN_CM = 1;
export const SIZE_MAX_CM = 1000;

// API ベースURL（Viteプロキシ経由）
export const API_BASE_URL = '/api';

// WebSocket ベースURL
export const WS_BASE_URL = `ws://${window.location.host}/ws`;

// ページング設定
export const PER_PAGE = 10;

// 問い合わせ一覧設定
export const CLOSED_INQUIRY_DISPLAY_LIMIT = 50;

// 事前ヒアリングの遷移先URLとして許可するスキーム
// 外部システムのURLのみを想定するため javascript: 等は受け付けない
export const PRE_HEARING_ALLOWED_URL_PROTOCOLS = ['http:', 'https:'];

// 事前ヒアリングの初期質問事項
// backend/app/bot/questions.py の INQUIRY_CATEGORY の選択肢と対応する
export const DEFAULT_PRE_HEARING_ITEMS: PreHearingItem[] = [
  { id: 1, label: '料金', target_url: null, is_builtin: true },
  { id: 2, label: 'その他', target_url: null, is_builtin: true },
];
