import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import styles from './OperatorLogin.module.css';

/**
 * オペレータログイン画面
 */
export function OperatorLogin() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!username || !password) {
      setError('ユーザー名とパスワードを入力してください');
      return;
    }

    setIsLoading(true);
    try {
      await login(username, password);
      navigate('/operator/inquiries');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ログインに失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>オペレータログイン</h1>
        <form onSubmit={handleSubmit} data-testid="login-form">
          <div className={styles.field}>
            <label htmlFor="username">ユーザー名</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="ユーザー名を入力"
              disabled={isLoading}
              data-testid="login-form-username"
            />
          </div>
          <div className={styles.field}>
            <label htmlFor="password">パスワード</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="パスワードを入力"
              disabled={isLoading}
              data-testid="login-form-password"
            />
          </div>
          {error && (
            <p className={styles.error} data-testid="login-form-error">
              {error}
            </p>
          )}
          <button
            type="submit"
            className={styles.button}
            disabled={isLoading}
            data-testid="login-form-submit-button"
          >
            {isLoading ? 'ログイン中...' : 'ログイン'}
          </button>
        </form>
      </div>
    </div>
  );
}
