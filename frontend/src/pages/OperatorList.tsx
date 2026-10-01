import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { OperatorNav } from '../components/OperatorNav';
import { Operator } from '../types';
import { API_BASE_URL } from '../constants';
import styles from './OperatorList.module.css';

/**
 * オペレータ一覧・削除画面
 */
export function OperatorList() {
  const { operator: currentOperator } = useAuth();
  const navigate = useNavigate();
  const [operators, setOperators] = useState<Operator[]>([]);

  // オペレータ一覧取得
  const fetchOperators = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/operators`, {
        credentials: 'include',
      });
      if (!response.ok) throw new Error('取得に失敗しました');
      const data = await response.json();
      setOperators(data);
    } catch (error) {
      console.error('オペレータ一覧取得エラー:', error);
    }
  }, []);

  useEffect(() => {
    fetchOperators();
  }, [fetchOperators]);

  // オペレータ削除処理
  const handleDelete = async (targetId: number) => {
    if (!confirm('このオペレータを削除しますか？')) return;

    try {
      const response = await fetch(`${API_BASE_URL}/operators/${targetId}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (!response.ok) {
        const error = await response.json();
        alert(error.detail || '削除に失敗しました');
        return;
      }
      // 一覧を再取得
      fetchOperators();
    } catch (error) {
      alert('削除に失敗しました');
    }
  };

  return (
    <div className={styles.container}>
      <OperatorNav />
      <main className={styles.main}>
        <div className={styles.header}>
          <h2 className={styles.title}>オペレータ管理</h2>
          <button
            className={styles.addButton}
            onClick={() => navigate('/operator/users/add')}
            data-testid="operator-add-navigate-button"
          >
            + オペレータを追加
          </button>
        </div>
        <table className={styles.table} data-testid="operator-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>ユーザー名</th>
              <th>表示名</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {operators.length === 0 ? (
              <tr>
                <td colSpan={4} className={styles.empty}>オペレータはいません</td>
              </tr>
            ) : (
              operators.map(op => (
                <tr key={op.id} data-testid={`operator-row-${op.id}`}>
                  <td>{op.id}</td>
                  <td>{op.username}</td>
                  <td>{op.display_name}</td>
                  <td>
                    {currentOperator && op.id !== currentOperator.id ? (
                      <button
                        className={styles.deleteButton}
                        onClick={() => handleDelete(op.id)}
                        data-testid={`operator-delete-button-${op.id}`}
                      >
                        削除
                      </button>
                    ) : (
                      <span className={styles.self}>（自分）</span>
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
