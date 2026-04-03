import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { TodayPage } from './pages/TodayPage'
import { PlanPage } from './pages/PlanPage'
import { AllocationPage } from './pages/AllocationPage'
import { SpendingPage } from './pages/SpendingPage'
import { useApi } from './hooks/useApi'
import type { InvestmentPolicy } from './types'

import { HoldingsPage } from './pages/HoldingsPage'

function AllocationGuard() {
  const { data: policy } = useApi<InvestmentPolicy>('/policy');
  if (!policy) return null;
  if (policy.targeting_mode === 'category') return <Navigate to="/" replace />;
  return <AllocationPage />;
}

function App() {
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
