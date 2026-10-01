import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { OperatorNav } from '../components/OperatorNav';
import { ChatWindow } from '../components/ChatWindow';
import { MessageInput } from '../components/MessageInput';
import { StatusBadge } from '../components/StatusBadge';
import { useChat } from '../hooks/useChat';
import { InquiryWithStatus, Message } from '../types';
import { API_BASE_URL } from '../constants';
import { DisplayStatus } from '../types';
import styles from './InquiryDetail.module.css';

/**
 * 問い合わせ詳細（チャット）画面
 * 自分の担当する問い合わせのみメッセージ送信可能
 */
export function InquiryDetail() {
  const { id } = useParams<{ id: string }>();
  const { operator } = useAuth();
  const navigate = useNavigate();
  const { messages: wsMessages, isConnected, sendMessage, connect, disconnect } = useChat();
  const [inquiry, setInquiry] = useState<InquiryWithStatus | null>(null);
  const [historyMessages, setHistoryMessages] = useState<Message[]>([]);

  // 問い合わせ情報取得
  useEffect(() => {
    if (!id || !operator) return;

    const fetchInquiry = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/inquiries/${id}`, {
          credentials: 'include',
        });
        if (!response.ok) {
          navigate('/operator/inquiries');
          return;
        }
        const data = await response.json();
        setInquiry(data);

        // メッセージ履歴取得
        const msgResponse = await fetch(`${API_BASE_URL}/inquiries/${id}/messages`, {
          credentials: 'include',
        });
        if (msgResponse.ok) {
          const msgs = await msgResponse.json();
          setHistoryMessages(msgs);
        }

        // 自分の担当かつ終了していない場合はWebSocket接続
        if (data.display_status === 'mine') {
          connect(Number(id), 'operator');
        }
      } catch {
        navigate('/operator/inquiries');
      }
    };

    fetchInquiry();

    return () => {
      disconnect();
    };
  }, [id, operator, navigate, connect, disconnect]);

  if (!inquiry) return null;

  // 履歴メッセージ + WebSocket受信メッセージを結合
  const allMessages = [...historyMessages, ...wsMessages];

  // 自分の担当かつ終了していない場合のみ送信可能
  const canSend = (inquiry.display_status as DisplayStatus) === 'mine' && isConnected;

  const inputPlaceholder = (): string => {
    if (canSend) return 'メッセージを入力...';

    switch (inquiry.display_status as DisplayStatus) {
      case 'closed':
        return 'この問い合わせは終了しています';
      case 'bot':
        return 'BOTが対応中です。完了までお待ちください';
      default:
        return 'この問い合わせの担当ではありません';
    }
  };

  return (
    <div className={styles.container}>
      <OperatorNav />
      <div className={styles.content}>
        <header className={styles.header}>
          <button
            className={styles.backButton}
            onClick={() => navigate('/operator/inquiries')}
            data-testid="inquiry-detail-back-button"
          >
            ← 一覧に戻る
          </button>
          <div className={styles.inquiryInfo} data-testid="inquiry-info">
            <span>問い合わせ #{inquiry.id}</span>
            <StatusBadge status={inquiry.display_status as DisplayStatus} />
          </div>
        </header>

        <ChatWindow messages={allMessages} currentUserType="operator" />

        <MessageInput onSend={sendMessage} disabled={!canSend} placeholder={inputPlaceholder()} />
      </div>
    </div>
  );
}
