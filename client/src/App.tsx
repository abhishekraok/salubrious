import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { TodayPage } from './pages/TodayPage'
import { PlanPage } from './pages/PlanPage'
import { AllocationPage } from './pages/AllocationPage'
import { SpendingPage } from './pages/SpendingPage'
import { LoginPage } from './pages/LoginPage'
import { useApi } from './hooks/useApi'
import { useAuth } from './contexts/AuthContext'
import type { InvestmentPolicy } from './types'

import { HoldingsPage } from './pages/HoldingsPage'

function AllocationGuard() {
  const { data: policy } = useApi<InvestmentPolicy>('/policy');
  if (!policy) return null;
  if (policy.targeting_mode === 'category') return <Navigate to="/" replace />;
  return <AllocationPage />;
}

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-calm-muted text-sm">Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<TodayPage />} />
        <Route path="/plan" element={<PlanPage />} />
        <Route path="/holdings" element={<HoldingsPage />} />
        <Route path="/allocation" element={<AllocationGuard />} />
        <Route path="/spending" element={<SpendingPage />} />
      </Route>
    </Routes>
  )
}

export default App
