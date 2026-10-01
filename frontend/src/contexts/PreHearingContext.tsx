import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { PreHearingItem, PreHearingItemInput } from '../types';
import { DEFAULT_PRE_HEARING_ITEMS, PRE_HEARING_ALLOWED_URL_PROTOCOLS } from '../constants';

interface PreHearingContextType {
  items: PreHearingItem[];
  addItem: (input: PreHearingItemInput) => PreHearingItem;
  removeItem: (id: number) => void;
}

const PreHearingContext = createContext<PreHearingContextType | null>(null);

// 事前ヒアリングコンテキストを使用するためのフック
export function usePreHearing(): PreHearingContextType {
  const context = useContext(PreHearingContext);
  if (!context) {
    throw new Error('usePreHearing は PreHearingProvider 内で使用してください');
  }
  return context;
}

// 遷移先URLの形式を検証する（不正な場合はエラーメッセージを返す）
function validateTargetUrl(targetUrl: string): string | null {
  let parsed: URL;
  try {
    parsed = new URL(targetUrl);
  } catch {
    return 'URLは http:// または https:// から始まる形式で入力してください';
  }
  if (!PRE_HEARING_ALLOWED_URL_PROTOCOLS.includes(parsed.protocol)) {
    return 'URLは http:// または https:// から始まる形式で入力してください';
  }
  return null;
}

interface PreHearingProviderProps {
  children: ReactNode;
}

export function PreHearingProvider({ children }: PreHearingProviderProps) {
  // バックエンド未実装のため、質問事項はブラウザのメモリ上のみで保持する（リロードで初期値に戻る）
  const [items, setItems] = useState<PreHearingItem[]>(DEFAULT_PRE_HEARING_ITEMS);

  // 質問事項の追加処理（検証に失敗した場合はエラーを投げる）
  const addItem = useCallback(
    (input: PreHearingItemInput): PreHearingItem => {
      const label = input.label.trim();
      const targetUrl = input.target_url.trim();

      const urlError = validateTargetUrl(targetUrl);
      if (urlError) {
        throw new Error(urlError);
      }
      if (items.some(item => item.label === label)) {
        throw new Error('同じボタン名の質問事項が既に存在します');
      }

      const nextId = items.reduce((maxId, item) => Math.max(maxId, item.id), 0) + 1;
      const created: PreHearingItem = {
        id: nextId,
        label,
        target_url: targetUrl,
        is_builtin: false,
      };
      setItems(prev => [...prev, created]);
      return created;
    },
    [items],
  );

  // 質問事項の削除処理（コード定義の項目は削除しない）
  const removeItem = useCallback((targetId: number) => {
    setItems(prev => prev.filter(item => item.id !== targetId || item.is_builtin));
  }, []);

  const value: PreHearingContextType = {
    items,
    addItem,
    removeItem,
  };

  return <PreHearingContext.Provider value={value}>{children}</PreHearingContext.Provider>;
}
