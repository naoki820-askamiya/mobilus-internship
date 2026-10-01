import { useNavigate } from 'react-router-dom';
import { OperatorNav } from '../components/OperatorNav';
import { usePreHearing } from '../contexts/PreHearingContext';
import styles from './PreHearingList.module.css';

/**
 * 事前ヒアリング管理画面
 * BOTが提示するボタンと、押下時にエンドユーザーへ案内するURLの対応を一覧・削除する
 */
export function PreHearingList() {
  const navigate = useNavigate();
  const { items, removeItem } = usePreHearing();

  // 質問事項削除処理
  const handleDelete = (targetId: number) => {
    if (!confirm('この質問事項を削除しますか？')) return;
    removeItem(targetId);
  };

  return (
    <div className={styles.container}>
      <OperatorNav />
      <main className={styles.main}>
        <div className={styles.header}>
          <h2 className={styles.title}>事前ヒアリング管理</h2>
          <button
            className={styles.addButton}
            onClick={() => navigate('/operator/pre-hearing/add')}
            data-testid="pre-hearing-add-navigate-button"
          >
            + 質問事項を追加
          </button>
        </div>
        <table className={styles.table} data-testid="pre-hearing-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>ボタン名</th>
              <th>遷移先URL</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={4} className={styles.empty}>質問事項はありません</td>
              </tr>
            ) : (
              items.map(item => (
                <tr key={item.id} data-testid={`pre-hearing-row-${item.id}`}>
                  <td>{item.id}</td>
                  <td>{item.label}</td>
                  <td>
                    {item.target_url ? (
                      <a
                        className={styles.url}
                        href={item.target_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {item.target_url}
                      </a>
                    ) : (
                      <span className={styles.noUrl}>（BOT内で処理）</span>
                    )}
                  </td>
                  <td>
                    {item.is_builtin ? (
                      <span className={styles.builtin}>（コード定義）</span>
                    ) : (
                      <button
                        className={styles.deleteButton}
                        onClick={() => handleDelete(item.id)}
                        data-testid={`pre-hearing-delete-button-${item.id}`}
                      >
                        削除
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </main>
    </div>
  );
}
