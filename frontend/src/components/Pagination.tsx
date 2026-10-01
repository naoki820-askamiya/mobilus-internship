import styles from './Pagination.module.css';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

/**
 * ページングコンポーネント
 */
export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <div className={styles.container} data-testid="pagination">
      <button
        className={styles.button}
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1}
        data-testid="pagination-prev"
      >
        ← 前へ
      </button>
      <span className={styles.info}>
        {currentPage} / {totalPages}
      </span>
      <button
        className={styles.button}
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
        data-testid="pagination-next"
      >
        次へ →
      </button>
    </div>
  );
}
