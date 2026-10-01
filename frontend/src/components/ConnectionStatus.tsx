import styles from './ConnectionStatus.module.css';

interface ConnectionStatusProps {
  isConnected: boolean;
}

/**
 * WebSocket接続状態表示コンポーネント
 */
export function ConnectionStatus({ isConnected }: ConnectionStatusProps) {
  return (
    <div className={styles.container} data-testid="connection-status">
      <span className={`${styles.dot} ${isConnected ? styles.connected : styles.disconnected}`} />
      <span className={styles.text}>
        {isConnected ? '接続中' : '未接続'}
      </span>
    </div>
  );
}
