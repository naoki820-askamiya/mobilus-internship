import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ReactNode } from 'react';

interface ProtectedRouteProps {
  children: ReactNode;
}

/**
 * 認証ガード付きルート
 * セッション確認中は何も表示せず、未認証の場合はログイン画面にリダイレクトする
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();

  // セッション確認中は何も表示しない（リダイレクトを防ぐ）
  if (isLoading) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/operator/login" replace />;
  }

  return <>{children}</>;
}
