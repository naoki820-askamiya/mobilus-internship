import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { OperatorNav } from '../components/OperatorNav';
import { usePreHearing } from '../contexts/PreHearingContext';
import { PreHearingItem } from '../types';
import styles from './PreHearingAdd.module.css';

/**
 * 事前ヒアリング質問事項の追加画面
 * ボタン名と、押下時にエンドユーザーへ案内する外部システムのURLを入力する
 */
export function PreHearingAdd() {
  const navigate = useNavigate();
  const { addItem } = usePreHearing();
  const [label, setLabel] = useState('');
  const [targetUrl, setTargetUrl] = useState('');
  const [addedItem, setAddedItem] = useState<PreHearingItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setAddedItem(null);

    if (!label.trim()) {
      setError('ボタン名を入力してください');
      return;
    }
    if (!targetUrl.trim()) {
      setError('遷移先URLを入力してください');
      return;
    }

    try {
      const created = addItem({ label, target_url: targetUrl });
      setAddedItem(created);
      setLabel('');
      setTargetUrl('');
    } catch (err) {
      setError(err instanceof Error ? err.message : '質問事項の追加に失敗しました');
    }
  };

  return (
    <div className={styles.container}>
      <OperatorNav />
      <main className={styles.main}>
        <h2 className={styles.title}>質問事項の追加</h2>

        <form onSubmit={handleSubmit} className={styles.form} data-testid="pre-hearing-add-form">
          <div className={styles.field}>
            <label htmlFor="label">ボタン名（エンドユーザーに表示）</label>
            <input
              id="label"
              type="text"
              value={label}
              onChange={e => setLabel(e.target.value)}
              placeholder="例: 分別について"
              data-testid="pre-hearing-add-label"
            />
          </div>
          <div className={styles.field}>
            <label htmlFor="targetUrl">遷移先URL（外部システム）</label>
            <input
              id="targetUrl"
              type="text"
              value={targetUrl}
              onChange={e => setTargetUrl(e.target.value)}
              placeholder="例: https://example.com/waste-sorting"
              data-testid="pre-hearing-add-target-url"
            />
          </div>

          {error && (
            <p className={styles.error} data-testid="pre-hearing-add-error">{error}</p>
          )}

          <button
            type="submit"
            className={styles.submitButton}
            data-testid="pre-hearing-add-submit-button"
          >
            質問事項を追加
          </button>
        </form>

        {addedItem && (
          <div className={styles.resultCard} data-testid="pre-hearing-add-result">
            <h3>質問事項を追加しました</h3>
            <p className={styles.notice}>
              「{addedItem.label}」が押されると、以下のURLをエンドユーザーに案内します。
            </p>
            <div className={styles.resultRow}>
              <code className={styles.resultUrl}>{addedItem.target_url}</code>
              <button
                className={styles.listButton}
                onClick={() => navigate('/operator/pre-hearing')}
                data-testid="pre-hearing-add-back-button"
              >
                一覧へ
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
