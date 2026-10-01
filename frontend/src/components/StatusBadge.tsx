import { DisplayStatus } from '../types';
import styles from './StatusBadge.module.css';

interface StatusBadgeProps {
  status: DisplayStatus;
}

const STATUS_LABELS: Record<DisplayStatus, string> = {
  waiting: '担当者未決定',
  mine: '自分の担当',
  others: '担当外',
  closed: '終了',
  bot: 'BOT対応中',
};

/**
 * ステータスバッジコンポーネント
 */
export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[status]}`} data-testid="status-badge">
      {STATUS_LABELS[status]}
    </span>
  );
}
