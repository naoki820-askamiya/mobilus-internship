import { Message } from '../types';
import { SENDER_TYPE } from '../constants';
import styles from './MessageBubble.module.css';

interface MessageBubbleProps {
  message: Message;
  isOwn: boolean;
  viewMode: 'enduser' | 'operator';
}

/**
 * メッセージ吹き出しコンポーネント
 * 自分のメッセージは右側、相手のメッセージは左側に表示
 * システムメッセージは中央に表示
 */
export function MessageBubble({ message, isOwn, viewMode }: MessageBubbleProps) {
  // システムメッセージは特別な表示
  if (message.sender_type === SENDER_TYPE.SYSTEM) {
    return (
      <div className={styles.system} data-testid="message-bubble-system">
        <span>{message.content}</span>
      </div>
    );
  }

  const time = new Date(message.created_at).toLocaleTimeString('ja-JP', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Asia/Tokyo',
  });

  // エンドユーザ画面では、オペレータのメッセージにアイコンを表示（名前は非表示）
  // オペレータ画面では、エンドユーザのメッセージに「お客様」と表示
  const renderSenderLabel = () => {
    if (isOwn) return null;

    // BOTのメッセージは画面を問わず自動応答とわかる表示にする
    if (message.sender_type === SENDER_TYPE.BOT) {
      return <span className={styles.senderIcon}>🤖 自動応答</span>;
    }

    if (viewMode === 'enduser') {
      // エンドユーザ画面: オペレータからのメッセージにヘッドセットアイコン
      return <span className={styles.senderIcon}>🎧 サポート</span>;
    } else {
      // オペレータ画面: エンドユーザからのメッセージ
      if (message.sender_type === SENDER_TYPE.ENDUSER) {
        return <span className={styles.senderName}>👤 お客様</span>;
      }
      // 他オペレータのメッセージ（通常はないが念のため）
      if (message.sender_name) {
        return <span className={styles.senderName}>{message.sender_name}</span>;
      }
    }
    return null;
  };

  return (
    <div
      className={`${styles.bubble} ${isOwn ? styles.own : styles.other}`}
      data-testid={`message-bubble-${isOwn ? 'own' : 'other'}`}
    >
      {renderSenderLabel()}
      <p className={styles.content}>{message.content}</p>
      <span className={styles.time}>{time}</span>
    </div>
  );
}
