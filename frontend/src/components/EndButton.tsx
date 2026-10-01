import styles from './EndButton.module.css';

interface EndButtonProps {
  onEnd: () => void;
  disabled: boolean;
}

/**
 * チャット終了ボタンコンポーネント
 */
export function EndButton({ onEnd, disabled }: EndButtonProps) {
  return (
    <button
      className={styles.button}
      onClick={onEnd}
      disabled={disabled}
      data-testid="end-chat-button"
    >
      チャットを終了する
    </button>
  );
}
