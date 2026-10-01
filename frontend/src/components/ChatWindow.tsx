import { useEffect, useRef } from 'react';
import { Message } from '../types';
import { MessageBubble } from './MessageBubble';
import styles from './ChatWindow.module.css';

interface ChatWindowProps {
  messages: Message[];
  currentUserType: 'enduser' | 'operator';
}

/**
 * メッセージ一覧表示コンポーネント
 * 新しいメッセージが追加されると自動スクロールする
 */
export function ChatWindow({ messages, currentUserType }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // 新しいメッセージ追加時に最下部へスクロール
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className={styles.container} data-testid="chat-window">
      {messages.length === 0 && (
        <p className={styles.empty}>メッセージはまだありません</p>
      )}
      {messages.map(message => {
        const isOwn =
          (currentUserType === 'enduser' && message.sender_type === 0) ||
          (currentUserType === 'operator' && message.sender_type === 1);
        return <MessageBubble key={message.id} message={message} isOwn={isOwn} viewMode={currentUserType} />;
      })}
      <div ref={bottomRef} />
    </div>
  );
}
