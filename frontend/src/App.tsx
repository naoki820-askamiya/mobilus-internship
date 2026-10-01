import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { PreHearingProvider } from './contexts/PreHearingContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { EndUserInquiry } from './pages/EndUserInquiry';
import { OperatorLogin } from './pages/OperatorLogin';
import { InquiryList } from './pages/InquiryList';
import { InquiryDetail } from './pages/InquiryDetail';
import { OperatorAdd } from './pages/OperatorAdd';
import { OperatorList } from './pages/OperatorList';
import { PreHearingList } from './pages/PreHearingList';
import { PreHearingAdd } from './pages/PreHearingAdd';

const SummaryBoard = lazy(() =>
  import('./pages/SummaryBoard').then((module) => ({default: module.SummaryBoard }))
);

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <PreHearingProvider>
          <Routes>
            {/* エンドユーザ画面 */}
            <Route path="/" element={<EndUserInquiry />} />

            {/* オペレータ ログイン画面 */}
            <Route path="/operator/login" element={<OperatorLogin />} />

            {/* オペレータ 認証必須画面 */}
            <Route
              path="/operator/inquiries"
              element={
                <ProtectedRoute>
                  <InquiryList />
                </ProtectedRoute>
              }
            />
            <Route
              path="/operator/inquiries/:id"
              element={
                <ProtectedRoute>
                  <InquiryDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/operator/users/add"
              element={
                <ProtectedRoute>
                  <OperatorAdd />
                </ProtectedRoute>
              }
            />
            <Route
              path="/operator/users"
              element={
                <ProtectedRoute>
                  <OperatorList />
                </ProtectedRoute>
              }
            />
            <Route
              path="/operator/pre-hearing/add"
              element={
                <ProtectedRoute>
                  <PreHearingAdd />
                </ProtectedRoute>
              }
            />
            <Route
              path="/operator/pre-hearing"
              element={
                <ProtectedRoute>
                  <PreHearingList />
                </ProtectedRoute>
              }
            />
            <Route
              path="/operator/summary-board"
              element={
                <ProtectedRoute>
                  <Suspense fallback={<p>読み込み中...</p>}>
                    <SummaryBoard />
                  </Suspense>
                </ProtectedRoute>
              }
            />
          </Routes>
        </PreHearingProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
