import { useState, FormEvent } from 'react';
import styles from './MessageInput.module.css';

interface MessageInputProps {
  onSend: (content: string) => void;
  disabled: boolean;
  placeholder?: string;
}

/**
 * メッセージ入力・送信コンポーネント
 * 空白のみのメッセージは送信できない
 */
export function MessageInput({ onSend, disabled, placeholder = 'メッセージを入力...' }: MessageInputProps) {
  const [content, setContent] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = content.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setContent('');
  };

  return (
    <form className={styles.container} onSubmit={handleSubmit} data-testid="message-input-form">
      <input
        type="text"
        className={styles.input}
        value={content}
        onChange={e => setContent(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        data-testid="message-input-field"
      />
      <button
        type="submit"
        className={styles.button}
        disabled={disabled || !content.trim()}
        data-testid="message-input-submit"
      >
        送信
      </button>
    </form>
  );
}
