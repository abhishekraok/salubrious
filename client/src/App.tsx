import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { TodayPage } from './pages/TodayPage'
import { PlanPage } from './pages/PlanPage'
import { AllocationPage } from './pages/AllocationPage'
import { SpendingPage } from './pages/SpendingPage'

import { HoldingsPage } from './pages/HoldingsPage'

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<TodayPage />} />
        <Route path="/plan" element={<PlanPage />} />
        <Route path="/holdings" element={<HoldingsPage />} />
        <Route path="/allocation" element={<AllocationPage />} />
        <Route path="/spending" element={<SpendingPage />} />

      </Route>
    </Routes>
  )
}

export default App
