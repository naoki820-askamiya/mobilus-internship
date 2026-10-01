import { useState, useCallback, useRef } from 'react';
import { BotAnswerPayload, BotQuestion, BotStepResponse, Message } from '../types';
import { API_BASE_URL, BOT_RESULT } from '../constants';

// BOT事前質問の進行状況
export type BotPhase = 'STARTING' | 'BOT' | 'OPERATOR' | 'COMPLETED' | 'ERROR';

interface UseBotChatReturn {
  inquiryId: number | null;
  phase: BotPhase;
  messages: Message[];
  question: BotQuestion | null;
  isSubmitting: boolean;
  error: string | null;
  start: () => Promise<void>;
  answer: (payload: BotAnswerPayload) => Promise<void>;
}

const START_ERROR_MESSAGE = 'チャットを開始できませんでした。時間をおいて再度お試しください。';
const ANSWER_ERROR_MESSAGE = '回答を送信できませんでした。通信環境をご確認ください。';

/**
 * BOT事前質問フック
 * REST APIで質問・回答をやり取りし、次の質問／オペレーター対応／終了へ遷移する
 */
export function useBotChat(): UseBotChatReturn {
  const [inquiryId, setInquiryId] = useState<number | null>(null);
  const [phase, setPhase] = useState<BotPhase>('STARTING');
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState<BotQuestion | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // StrictModeの二重実行や連打で問い合わせ・回答が重複しないようにする
  const hasStartedRef = useRef(false);
  const isSubmittingRef = useRef(false);
  const inquiryIdRef = useRef<number | null>(null);
  const questionRef = useRef<BotQuestion | null>(null);

  const applyStep = useCallback((step: BotStepResponse) => {
    setMessages(prev => [...prev, ...step.messages]);

    if (step.result === BOT_RESULT.QUESTION) {
      questionRef.current = step.question;
      setQuestion(step.question);
      setPhase('BOT');
      return;
    }

    questionRef.current = null;
    setQuestion(null);
    setPhase(step.result === BOT_RESULT.OPERATOR ? 'OPERATOR' : 'COMPLETED');
  }, []);

  const start = useCallback(async () => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;

    try {
      const response = await fetch(`${API_BASE_URL}/chat/start`, { method: 'POST' });
      if (!response.ok) throw new Error(START_ERROR_MESSAGE);

      const step: BotStepResponse = await response.json();
      inquiryIdRef.current = step.inquiry_id;
      setInquiryId(step.inquiry_id);
      applyStep(step);
    } catch {
      setError(START_ERROR_MESSAGE);
      setPhase('ERROR');
    }
  }, [applyStep]);

  const answer = useCallback(async (payload: BotAnswerPayload) => {
    const currentInquiryId = inquiryIdRef.current;
    const currentQuestion = questionRef.current;
    if (currentInquiryId === null || currentQuestion === null || isSubmittingRef.current) return;

    isSubmittingRef.current = true;
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/chat/${currentInquiryId}/bot/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state: currentQuestion.state, answer: payload }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        setError(typeof body?.detail === 'string' ? body.detail : ANSWER_ERROR_MESSAGE);
        return;
      }

      applyStep(await response.json());
    } catch {
      setError(ANSWER_ERROR_MESSAGE);
    } finally {
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    }
  }, [applyStep]);

  return { inquiryId, phase, messages, question, isSubmitting, error, start, answer };
}
