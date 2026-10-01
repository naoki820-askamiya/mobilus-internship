import { Operator, Inquiry, Message, InquiryWithStatus } from '../types';
import { INQUIRY_STATUS, SENDER_TYPE } from '../constants';

// モックオペレータ
export const mockOperators: Operator[] = [
  { id: 1, username: 'operator1', display_name: '田中太郎' },
  { id: 2, username: 'operator2', display_name: '鈴木花子' },
  { id: 3, username: 'operator3', display_name: '佐藤次郎' },
];

// モック問い合わせ
export const mockInquiries: Inquiry[] = [
  { id: 1, status: INQUIRY_STATUS.WAITING, assigned_operator_id: null, created_at: '2026-07-17T09:00:00Z', closed_at: null, bot_state: null },
  { id: 2, status: INQUIRY_STATUS.ACTIVE, assigned_operator_id: 1, created_at: '2026-07-17T09:05:00Z', closed_at: null, bot_state: null },
  { id: 3, status: INQUIRY_STATUS.ACTIVE, assigned_operator_id: 2, created_at: '2026-07-17T09:10:00Z', closed_at: null, bot_state: null },
  { id: 4, status: INQUIRY_STATUS.CLOSED, assigned_operator_id: 1, created_at: '2026-07-17T08:00:00Z', closed_at: '2026-07-17T08:30:00Z', bot_state: null },
  { id: 5, status: INQUIRY_STATUS.WAITING, assigned_operator_id: null, created_at: '2026-07-17T09:15:00Z', closed_at: null, bot_state: null },
  { id: 6, status: INQUIRY_STATUS.BOT, assigned_operator_id: null, created_at: '2026-07-17T09:20:00Z', closed_at: null, bot_state: 'SIZE_QUESTION' },
];

// モックメッセージ
export const mockMessages: Message[] = [
  { id: 1, inquiry_id: 2, sender_type: SENDER_TYPE.ENDUSER, sender_name: null, content: 'こんにちは、商品について質問があります。', created_at: '2026-07-17T09:05:30Z' },
  { id: 2, inquiry_id: 2, sender_type: SENDER_TYPE.OPERATOR, sender_name: '田中太郎', content: 'お問い合わせありがとうございます。どのような商品についてでしょうか？', created_at: '2026-07-17T09:06:00Z' },
  { id: 3, inquiry_id: 2, sender_type: SENDER_TYPE.ENDUSER, sender_name: null, content: '注文番号12345の商品の配送状況を教えてください。', created_at: '2026-07-17T09:06:30Z' },
  { id: 4, inquiry_id: 2, sender_type: SENDER_TYPE.OPERATOR, sender_name: '田中太郎', content: '確認いたします。少々お待ちください。', created_at: '2026-07-17T09:07:00Z' },
];

// ステータス算出ヘルパー（現在のオペレータIDに基づく）
export function computeDisplayStatus(inquiry: Inquiry, currentOperatorId: number): InquiryWithStatus {
  let display_status: InquiryWithStatus['display_status'];

  if (inquiry.status === INQUIRY_STATUS.CLOSED) {
    display_status = 'closed';
  } else if (inquiry.status === INQUIRY_STATUS.BOT) {
    display_status = 'bot';
  } else if (inquiry.status === INQUIRY_STATUS.WAITING) {
    display_status = 'waiting';
  } else if (inquiry.assigned_operator_id === currentOperatorId) {
    display_status = 'mine';
  } else {
    display_status = 'others';
  }

  return { ...inquiry, display_status };
}
