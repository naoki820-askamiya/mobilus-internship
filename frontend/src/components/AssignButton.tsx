import styles from './AssignButton.module.css';

interface AssignButtonProps {
  inquiryId: number;
  onAssign: (inquiryId: number) => void;
  disabled: boolean;
}

/**
 * 「担当する」ボタンコンポーネント
 */
export function AssignButton({ inquiryId, onAssign, disabled }: AssignButtonProps) {
  return (
    <button
      className={styles.button}
      onClick={() => onAssign(inquiryId)}
      disabled={disabled}
      data-testid={`assign-button-${inquiryId}`}
    >
      担当する
    </button>
  );
}
