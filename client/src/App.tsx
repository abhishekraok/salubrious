import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { TodayPage } from './pages/TodayPage'
import { PlanPage } from './pages/PlanPage'
import { AllocationPage } from './pages/AllocationPage'
import { SpendingPage } from './pages/SpendingPage'
import { ReviewPage } from './pages/ReviewPage'

import { HoldingsPage } from './pages/HoldingsPage'
import { InsightsPage } from './pages/InsightsPage'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<TodayPage />} />
        <Route path="/plan" element={<PlanPage />} />
        <Route path="/holdings" element={<HoldingsPage />} />
        <Route path="/allocation" element={<AllocationPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/spending" element={<SpendingPage />} />
        <Route path="/review" element={<ReviewPage />} />

      </Route>
    </Routes>
  )
}

export default App
