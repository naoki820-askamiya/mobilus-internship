import { useState, useCallback, useRef, useEffect } from 'react';
import { Message } from '../types';
import { WS_BASE_URL } from '../constants';

interface UseChatReturn {
  messages: Message[];
  isConnected: boolean;
  sendMessage: (content: string) => void;
  connect: (inquiryId: number, userType: 'enduser' | 'operator') => void;
  disconnect: () => void;
}

/**
 * チャット用WebSocket通信フック
 * WebSocket接続の確立・切断・メッセージ送受信を管理する
 */
export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const inquiryIdRef = useRef<number>(0);

  // WebSocket接続開始
  const connect = useCallback((inquiryId: number, userType: 'enduser' | 'operator') => {
    // 既存接続があれば閉じる
    if (wsRef.current) {
      wsRef.current.close();
    }

    const path = userType === 'enduser'
      ? `${WS_BASE_URL}/chat/enduser/${inquiryId}`
      : `${WS_BASE_URL}/chat/operator/${inquiryId}`;

    const ws = new WebSocket(path);
    wsRef.current = ws;
    inquiryIdRef.current = inquiryId;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'connected') {
        // 新規問い合わせの場合、サーバーから割り当てられたIDを受け取る
        inquiryIdRef.current = data.inquiry_id;
      } else if (data.type === 'message') {
        // 新しいメッセージを追加
        const msg: Message = {
          id: data.id,
          inquiry_id: data.inquiry_id,
          sender_type: data.sender_type,
          sender_name: data.sender_name,
          content: data.content,
          created_at: data.created_at,
        };
        setMessages(prev => [...prev, msg]);
      } else if (data.type === 'closed') {
        // 問い合わせ終了通知
        setIsConnected(false);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onerror = () => {
      setIsConnected(false);
    };
  }, []);

  // WebSocket接続終了
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      // 明示的な終了メッセージを送信
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'close' }));
      }
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // メッセージ送信
  const sendMessage = useCallback((content: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', content }));
    }
  }, []);

  // コンポーネントアンマウント時にクリーンアップ
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { messages, isConnected, sendMessage, connect, disconnect };
}
