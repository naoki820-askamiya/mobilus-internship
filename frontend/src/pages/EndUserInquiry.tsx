import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ChatWindow } from '../components/ChatWindow';
import { MessageInput } from '../components/MessageInput';
import { BotQuestionInput } from '../components/BotQuestionInput';
import { ConnectionStatus } from '../components/ConnectionStatus';
import { EndButton } from '../components/EndButton';
import { WaitTimeChart } from '../components/WaitTimeChart';
import { API_BASE_URL } from '../constants';
import { useChat } from '../hooks/useChat';
import { useBotChat } from '../hooks/useBotChat';
import { WaitTimeHistoryResponse, WaitTimeResponse } from '../types';
import styles from './EndUserInquiry.module.css';

const WAIT_TIME_POLLING_INTERVAL_MS = 60 * 1000;

function formatWaitTimeLabel(waitTime: WaitTimeResponse | null): string {
  if (waitTime === null) return '取得中...';
  if (waitTime.estimated_wait_minutes === null) {
    return '対応できるオペレーターがいません';
  }
  return `約${waitTime.estimated_wait_minutes}分`;
}

/**
 * エンドユーザ向け問い合わせページ
 * 待ち時間確認 → チャット開始までを1画面で段階的に表示する
 */
export function EndUserInquiry() {
  const [hasStartedChat, setHasStartedChat] = useState(false);
  const [isClosed, setIsClosed] = useState(false);
  const connectedInquiryIdRef = useRef<number | null>(null);

  const [waitTime, setWaitTime] = useState<WaitTimeResponse | null>(null);
  const [waitTimeHistory, setWaitTimeHistory] =
    useState<WaitTimeHistoryResponse | null>(null);
  const [isWaitTimeLoading, setIsWaitTimeLoading] = useState(true);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [waitTimeError, setWaitTimeError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const { messages: chatMessages, isConnected, sendMessage, connect, disconnect } = useChat();
  const {
    inquiryId,
    phase,
    messages: botMessages,
    question,
    isSubmitting,
    error,
    start,
    answer,
  } = useBotChat();

  const fetchWaitTime = useCallback(async (showLoadingIndicator: boolean) => {
    if (showLoadingIndicator) setIsWaitTimeLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/wait-time`);
      if (!response.ok) throw new Error('現在の待ち時間の取得に失敗しました');

      const data: WaitTimeResponse = await response.json();
      setWaitTime(data);
      setWaitTimeError(null);
    } catch (fetchError) {
      console.error('現在の待ち時間取得エラー:', fetchError);
      setWaitTimeError('現在の待ち時間を取得できませんでした。');
    } finally {
      if (showLoadingIndicator) setIsWaitTimeLoading(false);
    }
  }, []);

  const fetchWaitTimeHistory = useCallback(async () => {
    setIsHistoryLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/wait-time/hourly`);
      if (!response.ok) throw new Error('待ち時間履歴の取得に失敗しました');

      const data: WaitTimeHistoryResponse = await response.json();
      setWaitTimeHistory(data);
      setHistoryError(null);
    } catch (fetchError) {
      console.error('待ち時間履歴取得エラー:', fetchError);
      setHistoryError('待ち時間履歴を取得できませんでした。');
    } finally {
      setIsHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (hasStartedChat) return;

    fetchWaitTime(true);

    const intervalId = setInterval(() => {
      fetchWaitTime(false);
    }, WAIT_TIME_POLLING_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [fetchWaitTime, hasStartedChat]);

  useEffect(() => {
    fetchWaitTimeHistory();
  }, [fetchWaitTimeHistory]);

  // ユーザー操作後にのみ BOT 事前質問を開始する
  useEffect(() => {
    if (!hasStartedChat) return;
    start();
  }, [hasStartedChat, start]);

  // 問い合わせ作成後に WebSocket へ接続する
  useEffect(() => {
    if (!hasStartedChat || inquiryId === null || connectedInquiryIdRef.current === inquiryId) {
      return;
    }
    connectedInquiryIdRef.current = inquiryId;
    connect(inquiryId, 'enduser');
  }, [hasStartedChat, inquiryId, connect]);

  // BOT だけで解決した場合はそのまま終了する
  useEffect(() => {
    if (phase !== 'COMPLETED') return;
    setIsClosed(true);
    disconnect();
  }, [phase, disconnect]);

  const messages = useMemo(
    () => [...botMessages, ...chatMessages],
    [botMessages, chatMessages]
  );

  const handleEnd = () => {
    setIsClosed(true);
    disconnect();
  };

  const renderWaitTime = () => {
    if (isWaitTimeLoading) {
      return <p className={styles.statusMessage}>読み込み中...</p>;
    }

    if (!waitTime) {
      return (
        <div className={styles.errorState} role="alert">
          <p>{waitTimeError}</p>
          <button
            className={styles.retryButton}
            type="button"
            onClick={() => fetchWaitTime(true)}
          >
            再読み込み
          </button>
        </div>
      );
    }

    return (
      <>
        {waitTimeError && (
          <p className={styles.warning} role="alert">
            {waitTimeError} 前回取得した情報を表示しています。
          </p>
        )}
        <p className={styles.waitTimeValue} data-testid="current-wait-time">
          {formatWaitTimeLabel(waitTime)}
        </p>
        <p className={styles.updatedAt}>更新日時: {waitTime.updated_at} JST</p>
      </>
    );
  };

  const renderWaitTimeHistory = () => {
    if (isHistoryLoading) {
      return <p className={styles.statusMessage}>読み込み中...</p>;
    }

    if (!waitTimeHistory) {
      return (
        <div className={styles.errorState} role="alert">
          <p>{historyError}</p>
          <button
            className={styles.retryButton}
            type="button"
            onClick={fetchWaitTimeHistory}
          >
            再読み込み
          </button>
        </div>
      );
    }

    if (waitTimeHistory.items.length === 0) {
      return (
        <p className={styles.statusMessage}>
          表示できる待ち時間データがありません
        </p>
      );
    }

    return <WaitTimeChart data={waitTimeHistory} />;
  };

  const renderInputArea = () => {
    if (isClosed) {
      return (
        <div className={styles.closedMessage}>
          チャットが終了しました。ご利用ありがとうございました。
        </div>
      );
    }

    if (phase === 'ERROR') {
      return <div className={styles.errorMessage}>{error}</div>;
    }

    if (phase === 'STARTING') {
      return <div className={styles.noticeMessage}>準備中です...</div>;
    }

    if (phase === 'BOT' && question !== null) {
      return (
        <BotQuestionInput
          question={question}
          disabled={isSubmitting}
          error={error}
          onAnswer={answer}
        />
      );
    }

    return (
      <MessageInput
        onSend={sendMessage}
        disabled={!isConnected}
        placeholder="メッセージを入力..."
      />
    );
  };

  const containerClassName = hasStartedChat
    ? `${styles.container} ${styles.containerChat}`
    : `${styles.container} ${styles.containerEntry}`;

  return (
    <div className={containerClassName}>
      <header className={styles.header}>
        <h1 className={styles.headerTitle}>お問い合わせチャット</h1>
        {hasStartedChat && (
          <div className={styles.headerActions}>
            <ConnectionStatus isConnected={isConnected && !isClosed} />
            <EndButton onEnd={handleEnd} disabled={isClosed} />
          </div>
        )}
      </header>

      {!hasStartedChat ? (
        <main className={styles.entryMain}>
          <section className={styles.card} aria-labelledby="current-wait-title">
            <h2 id="current-wait-title" className={styles.sectionTitle}>
              現在の想定待ち時間
            </h2>
            {renderWaitTime()}
            <p className={styles.note}>
              表示される待ち時間は目安です。混雑状況により変動します。
            </p>
            <button
              className={styles.chatButton}
              type="button"
              onClick={() => setHasStartedChat(true)}
            >
              チャットを開始する
            </button>
          </section>

          <section className={styles.card} aria-labelledby="history-title">
            <h2 id="history-title" className={styles.sectionTitle}>
              時間帯別の待ち時間の目安
            </h2>
            <p className={styles.description}>
              過去の利用状況をもとに、時間帯ごとの待ち時間の傾向をご案内しています。
              比較的つながりやすい時間帯を、次回のご利用の目安としてお役立てください。
            </p>
            {renderWaitTimeHistory()}
            <p className={styles.note}>
              実際の待ち時間は当日の状況により変動します。
            </p>
          </section>
        </main>
      ) : (
        <div className={styles.chatBody}>
          <ChatWindow messages={messages} currentUserType="enduser" />
          {renderInputArea()}
        </div>
      )}
    </div>
  );
}
