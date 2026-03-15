import { Navigate, Route, Routes } from 'react-router-dom'

import { useSession } from './context/SessionContext'
import { AdminLayout } from './layouts/AdminLayout'
import { CollectionsPage } from './pages/CollectionsPage'
import { DashboardPage } from './pages/DashboardPage'
import { DisplayPage } from './pages/DisplayPage'
import { DisplaySettingsPage } from './pages/DisplaySettingsPage'
import { LibraryPage } from './pages/LibraryPage'
import { LoginPage } from './pages/LoginPage'
import { SetupPage } from './pages/SetupPage'
import { SettingsPage } from './pages/SettingsPage'
import { SourcesPage } from './pages/SourcesPage'

function LoadingScreen() {
  return (
    <div className="auth-loading">
      <p>Loading…</p>
    </div>
  )
}

function RootRedirect() {
  const { state } = useSession()
  if (state.status === 'loading') return <LoadingScreen />
  if (!state.bootstrapped) return <Navigate to="/setup" replace />
  if (state.status === 'anonymous') return <Navigate to="/login" replace />
  return <Navigate to="/admin" replace />
}

function RequireAdmin() {
  const { state } = useSession()
  if (state.status === 'loading') return <LoadingScreen />
  if (!state.bootstrapped) return <Navigate to="/setup" replace />
  if (state.status !== 'authenticated') return <Navigate to="/login" replace />
  return <AdminLayout />
}

function RequireSetup() {
  const { state } = useSession()
  if (state.status === 'loading') return <LoadingScreen />
  if (state.bootstrapped) {
    return <Navigate to={state.status === 'authenticated' ? '/admin' : '/login'} replace />
  }
  return <SetupPage />
}

function RequireUnauthenticated() {
  const { state } = useSession()
  if (state.status === 'loading') return <LoadingScreen />
  if (!state.bootstrapped) return <Navigate to="/setup" replace />
  if (state.status === 'authenticated') return <Navigate to="/admin" replace />
  return <LoginPage />
}

export default function App() {
  return (
    <Routes>
      <Route path="/display" element={<DisplayPage />} />
      <Route path="/setup" element={<RequireSetup />} />
      <Route path="/login" element={<RequireUnauthenticated />} />
      <Route path="/admin" element={<RequireAdmin />}>
        <Route index element={<DashboardPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="collections" element={<CollectionsPage />} />
        <Route path="sources" element={<SourcesPage />} />
        <Route path="display-settings" element={<DisplaySettingsPage />} />
      </Route>
      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
