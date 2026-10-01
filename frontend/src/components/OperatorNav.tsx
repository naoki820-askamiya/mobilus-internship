import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { OPERATOR_AVAILABILITY_STATUS } from '../types';
import styles from './OperatorNav.module.css';

/**
 * オペレータ用ナビゲーションバー
 */
export function OperatorNav() {
  const { operator, logout, updateAvailability } = useAuth();
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAvailable =
    operator?.availability_status === OPERATOR_AVAILABILITY_STATUS.AVAILABLE;

  const handleLogout = async () => {
    await logout();
  };

  const handleAvailabilityToggle = async () => {
    const nextStatus = isAvailable
      ? OPERATOR_AVAILABILITY_STATUS.AWAY
      : OPERATOR_AVAILABILITY_STATUS.AVAILABLE;

    setIsUpdating(true);
    setError(null);
    try {
      await updateAvailability(nextStatus);
    } catch (updateError) {
      setError(
        updateError instanceof Error
          ? updateError.message
          : '稼働状態の更新に失敗しました',
      );
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <nav className={styles.nav} data-testid="operator-nav">
      <div className={styles.left}>
        <Link to="/operator/inquiries" className={styles.link}>問い合わせ一覧</Link>
        <Link to="/operator/summary-board" className={styles.link}>サマリーボード</Link>
        <Link to="/operator/users" className={styles.link}>オペレータ管理</Link>
        <Link to="/operator/pre-hearing" className={styles.link}>事前ヒアリング</Link>
      </div>
      <div className={styles.accountArea}>
        <div className={styles.right}>
          <button
            type="button"
            className={styles.availabilityButton}
            onClick={handleAvailabilityToggle}
            disabled={isUpdating}
            data-testid="operator-nav-availability-toggle"
          >
            {isUpdating ? '更新中...' : isAvailable ? '離席にする' : '稼働にする'}
          </button>
          <span
            className={`${styles.availabilityStatus} ${
              isAvailable ? styles.available : styles.away
            }`}
            data-testid="operator-nav-availability-status"
          >
            {isAvailable ? '稼働' : '離席'}
          </span>
          <span className={styles.operatorName}>{operator?.display_name}</span>
          <button
            type="button"
            className={styles.logoutButton}
            onClick={handleLogout}
            data-testid="operator-nav-logout-button"
          >
            ログアウト
          </button>
        </div>
        {error && (
          <p
            className={styles.availabilityError}
            aria-live="polite"
            data-testid="operator-nav-availability-error"
          >
            {error}
          </p>
        )}
      </div>
    </nav>
  );
}
