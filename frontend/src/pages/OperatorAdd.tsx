import { useState, FormEvent } from 'react';
import { OperatorNav } from '../components/OperatorNav';
import { API_BASE_URL } from '../constants';
import styles from './OperatorAdd.module.css';

/**
 * オペレータ追加画面
 * username と display_name を入力し、パスワードが自動発行される
 */
export function OperatorAdd() {
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setGeneratedPassword(null);

    if (!username.trim()) {
      setError('ユーザー名を入力してください');
      return;
    }
    if (!displayName.trim()) {
      setError('表示名を入力してください');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/operators`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: username.trim(), display_name: displayName.trim() }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'オペレータの追加に失敗しました');
      }

      const data = await response.json();
      setGeneratedPassword(data.generated_password);
      setUsername('');
      setDisplayName('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'オペレータの追加に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    if (generatedPassword) {
      navigator.clipboard.writeText(generatedPassword);
    }
  };

  return (
    <div className={styles.container}>
      <OperatorNav />
      <main className={styles.main}>
        <h2 className={styles.title}>オペレータ追加</h2>

        <form onSubmit={handleSubmit} className={styles.form} data-testid="operator-add-form">
          <div className={styles.field}>
            <label htmlFor="username">ユーザー名（ログインID）</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="例: operator4"
              disabled={isLoading}
              data-testid="operator-add-username"
            />
          </div>
          <div className={styles.field}>
            <label htmlFor="displayName">表示名</label>
            <input
              id="displayName"
              type="text"
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              placeholder="例: 山田太郎"
              disabled={isLoading}
              data-testid="operator-add-display-name"
            />
          </div>

          {error && (
            <p className={styles.error} data-testid="operator-add-error">{error}</p>
          )}

          <button
            type="submit"
            className={styles.submitButton}
            disabled={isLoading}
            data-testid="operator-add-submit-button"
          >
            {isLoading ? '作成中...' : 'オペレータを追加'}
          </button>
        </form>

        {generatedPassword && (
          <div className={styles.passwordCard} data-testid="operator-add-password-display">
            <h3>パスワードが発行されました</h3>
            <p className={styles.notice}>
              このパスワードは一度だけ表示されます。新しいオペレータに渡してください。
            </p>
            <div className={styles.passwordRow}>
              <code className={styles.password}>{generatedPassword}</code>
              <button
                className={styles.copyButton}
                onClick={handleCopy}
                data-testid="operator-add-copy-password"
              >
                コピー
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
