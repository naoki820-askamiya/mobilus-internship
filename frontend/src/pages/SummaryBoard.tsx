import { useCallback, useEffect, useRef, useState } from 'react';
import { HourlyResponseTimeChart } from '../components/HourlyResponseTimeChart';
import { HourlySessionChart } from '../components/HourlySessionChart';
import { OperatorNav } from '../components/OperatorNav';
import { API_BASE_URL } from '../constants';
import { DailySummaryResponse } from '../types';
import { formatDuration } from '../utils/formatDuration';
import styles from './SummaryBoard.module.css';

const JST_TIME_ZONE = 'Asia/Tokyo';

function getTodayInJst(): string {
  const parts = new Intl.DateTimeFormat('ja-JP', {
    timeZone: JST_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date());
  const year = parts.find((part) => part.type === 'year')?.value;
  const month = parts.find((part) => part.type === 'month')?.value;
  const day = parts.find((part) => part.type === 'day')?.value;

  return `${year}-${month}-${day}`;
}

/**
 * 選択日のセッション数と初回応答時間を表示するオペレータ向け画面
 */
export function SummaryBoard() {
  const [selectedDate, setSelectedDate] = useState(getTodayInJst);
  const [summary, setSummary] = useState<DailySummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const latestRequestIdRef = useRef(0);

  const fetchSummary = useCallback(async (date: string) => {
    const requestId = latestRequestIdRef.current + 1;
    latestRequestIdRef.current = requestId;
    setIsLoading(true);
    setSummary(null);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/summary?date=${encodeURIComponent(date)}`,
        { credentials: 'include' }
      );
      if (!response.ok) {
        throw new Error('サマリーの取得に失敗しました');
      }

      const data: DailySummaryResponse = await response.json();
      if (requestId === latestRequestIdRef.current) {
        setSummary(data);
      }
    } catch (fetchError) {
      console.error('サマリー取得エラー:', fetchError);
      if (requestId === latestRequestIdRef.current) {
        setError('サマリーを取得できませんでした。');
      }
    } finally {
      if (requestId === latestRequestIdRef.current) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    fetchSummary(selectedDate);
  }, [fetchSummary, selectedDate]);

  const renderContent = () => {
    if (isLoading) {
      return <p className={styles.statusMessage}>読み込み中...</p>;
    }

    if (!summary) {
      return (
        <div className={styles.errorState} role="alert">
          <p>{error}</p>
          <button
            className={styles.retryButton}
            type="button"
            onClick={() => fetchSummary(selectedDate)}
          >
            再読み込み
          </button>
        </div>
      );
    }

    return (
      <>
        <section className={styles.kpiGrid} aria-label="選択日の集計">
          <div className={styles.kpiCard}>
            <p className={styles.kpiLabel}>合計セッション数</p>
            <p className={styles.kpiValue} data-testid="total-sessions">
              {summary.total_sessions}件
            </p>
          </div>
          <div className={styles.kpiCard}>
            <p className={styles.kpiLabel}>平均初回応答時間</p>
            <p className={styles.kpiValue} data-testid="average-response-time">
              {summary.average_first_response_seconds === null
                ? 'データなし'
                : formatDuration(summary.average_first_response_seconds)}
            </p>
          </div>
        </section>

        <section className={styles.chartCard}>
          <h2 className={styles.chartTitle}>1時間ごとのセッション数</h2>
          <HourlySessionChart data={summary.hourly} />
        </section>

        <section className={styles.chartCard}>
          <h2 className={styles.chartTitle}>1時間ごとの平均初回応答時間</h2>
          <HourlyResponseTimeChart data={summary.hourly} />
        </section>
      </>
    );
  };

  return (
    <div className={styles.container}>
      <OperatorNav />
      <main className={styles.main}>
        <div className={styles.header}>
          <h1 className={styles.title}>サマリーボード</h1>
          <label className={styles.dateField}>
            集計日
            <input
              className={styles.dateInput}
              type="date"
              value={selectedDate}
              onChange={(event) => {
                if (event.target.value) setSelectedDate(event.target.value);
              }}
              required
            />
          </label>
        </div>
        {renderContent()}
      </main>
    </div>
  );
}
