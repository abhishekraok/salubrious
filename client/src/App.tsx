import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import { Layout } from './components/Layout'
import { LoginPage } from './pages/LoginPage'
import { TodayPage } from './pages/TodayPage'
import { PlanPage } from './pages/PlanPage'
import { AllocationPage } from './pages/AllocationPage'
import { SpendingPage } from './pages/SpendingPage'
import { ReviewPage } from './pages/ReviewPage'
import { SettingsPage } from './pages/SettingsPage'
import { HoldingsPage } from './pages/HoldingsPage'
import { InsightsPage } from './pages/InsightsPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return <div className="min-h-screen bg-calm-bg flex items-center justify-center text-calm-muted">Loading...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<TodayPage />} />
        <Route path="/plan" element={<PlanPage />} />
        <Route path="/holdings" element={<HoldingsPage />} />
        <Route path="/allocation" element={<AllocationPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/spending" element={<SpendingPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}

export default App
