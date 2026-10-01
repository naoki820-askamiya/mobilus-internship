import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { OperatorNav } from '../components/OperatorNav';
import { StatusBadge } from '../components/StatusBadge';
import { AssignButton } from '../components/AssignButton';
import { InquiryWithStatus } from '../types';
import { API_BASE_URL, CLOSED_INQUIRY_DISPLAY_LIMIT } from '../constants';
import styles from './InquiryList.module.css';

// ポーリング間隔（ミリ秒）
const POLLING_INTERVAL = 5000;

function getLatestInquiryId(inquiries: InquiryWithStatus[]): number {
  return inquiries.reduce(
    (latestId, inquiry) => Math.max(latestId, inquiry.id),
    0
  );
}

/**
 * 問い合わせ一覧画面
 * 5秒間隔で新しい問い合わせがないかポーリングし、あればバナーで通知する
 */
export function InquiryList() {
  const { operator } = useAuth();
  const navigate = useNavigate();
  const [inquiries, setInquiries] = useState<InquiryWithStatus[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasNewInquiry, setHasNewInquiry] = useState(false);
  const knownLatestOpenIdRef = useRef(0);
  const hasInitializedLatestOpenIdRef = useRef(false);

  // 問い合わせ一覧取得
  const fetchInquiries = useCallback(async () => {
    if (!operator) return;
    setIsLoading(true);
    setHasNewInquiry(false);

    try {
      const [openResponse, closedResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/inquiries/open`, { credentials: 'include' }),
        fetch(`${API_BASE_URL}/inquiries/closed`, { credentials: 'include' }),
      ]);
      if (!openResponse.ok || !closedResponse.ok) {
        throw new Error('取得に失敗しました');
      }

      const openItems: InquiryWithStatus[] = await openResponse.json();
      const closedItems: InquiryWithStatus[] = await closedResponse.json();

      setInquiries([...openItems, ...closedItems]);
      knownLatestOpenIdRef.current = getLatestInquiryId(openItems);
      hasInitializedLatestOpenIdRef.current = true;
    } catch (error) {
      console.error('問い合わせ一覧取得エラー:', error);
    } finally {
      setIsLoading(false);
    }
  }, [operator]);

  useEffect(() => {
    fetchInquiries();
  }, [fetchInquiries]);

  // 5秒間隔のポーリングで新しい問い合わせを検知
  useEffect(() => {
    if (!operator) return;

    const intervalId = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/inquiries/open`, {
          credentials: 'include',
        });
        if (!response.ok) return;

        const data: InquiryWithStatus[] = await response.json();
        const latestOpenId = getLatestInquiryId(data);

        // 初回一覧取得に失敗しても、既存データを新着と誤認しないよう基準値だけ設定する
        if (!hasInitializedLatestOpenIdRef.current) {
          knownLatestOpenIdRef.current = latestOpenId;
          hasInitializedLatestOpenIdRef.current = true;
          return;
        }

        if (latestOpenId > knownLatestOpenIdRef.current) {
          setHasNewInquiry(true);
        }
      } catch {
        // ポーリングのエラーは無視
      }
    }, POLLING_INTERVAL);

    return () => clearInterval(intervalId);
  }, [operator]);

  // バナークリックで一覧を更新
  const handleRefresh = () => {
    fetchInquiries();
  };

  // 担当取得処理
  const handleAssign = async (inquiryId: number) => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/inquiries/${inquiryId}/assign`,
        { method: 'POST', credentials: 'include' }
      );
      if (!response.ok) {
        const error = await response.json();
        alert(error.detail || '担当取得に失敗しました');
        return;
      }
      fetchInquiries();
    } catch {
      alert('担当取得に失敗しました');
    }
  };

  // 問い合わせ詳細へ遷移
  const handleRowClick = (inquiryId: number) => {
    navigate(`/operator/inquiries/${inquiryId}`);
  };

  return (
    <div className={styles.container}>
      <OperatorNav />
      <main className={styles.main}>
        <h2 className={styles.title}>問い合わせ一覧</h2>

        {/* 新しい問い合わせ通知バナー */}
        {hasNewInquiry && (
          <div
            className={styles.notificationBanner}
            onClick={handleRefresh}
            data-testid="new-inquiry-notification"
          >
            🔔 新しい問い合わせがあります。クリックして更新
          </div>
        )}

        {isLoading ? (
          <p>読み込み中...</p>
        ) : (
          <>
            <table className={styles.table} data-testid="inquiry-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>ステータス</th>
                  <th>作成日時</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {inquiries.length === 0 ? (
                  <tr>
                    <td colSpan={4} className={styles.empty}>問い合わせはありません</td>
                  </tr>
                ) : (
                  inquiries.map(inquiry => (
                    <tr
                      key={inquiry.id}
                      className={styles.row}
                      onClick={() => handleRowClick(inquiry.id)}
                      data-testid={`inquiry-row-${inquiry.id}`}
                    >
                      <td>#{inquiry.id}</td>
                      <td><StatusBadge status={inquiry.display_status} /></td>
                      <td>{new Date(inquiry.created_at).toLocaleString('ja-JP')}</td>
                      <td onClick={e => e.stopPropagation()}>
                        {inquiry.display_status === 'waiting' && (
                          <AssignButton
                            inquiryId={inquiry.id}
                            onAssign={handleAssign}
                            disabled={false}
                          />
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
            <p>
              完了済みは最新{CLOSED_INQUIRY_DISPLAY_LIMIT}件まで表示しています
            </p>
          </>
        )}
      </main>
    </div>
  );
}
