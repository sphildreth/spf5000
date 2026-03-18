import { Component, type ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { useSession } from './context/SessionContext'
import { AdminLayout } from './layouts/AdminLayout'
import { BackupsPage } from './pages/BackupsPage'
import { CollectionsPage } from './pages/CollectionsPage'
import { DashboardPage } from './pages/DashboardPage'
import { DisplayPage } from './pages/DisplayPage'
import { DisplaySettingsPage } from './pages/DisplaySettingsPage'
import { LibraryPage } from './pages/LibraryPage'
import { LoginPage } from './pages/LoginPage'
import { SetupPage } from './pages/SetupPage'
import { SettingsPage } from './pages/SettingsPage'
import { SourcesPage } from './pages/SourcesPage'
import { WeatherPage } from './pages/WeatherPage'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: { componentStack?: string }) {
    console.error('Uncaught error:', error, errorInfo)
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          <h1>Something went wrong</h1>
          <p style={{ color: '#666' }}>
            {this.state.error?.message ?? 'An unexpected error occurred.'}
          </p>
        </div>
      )
    }
    return this.props.children
  }
}

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
    <ErrorBoundary>
      <Routes>
        <Route path="/display" element={<DisplayPage />} />
        <Route path="/setup" element={<RequireSetup />} />
        <Route path="/login" element={<RequireUnauthenticated />} />
        <Route path="/admin" element={<RequireAdmin />}>
          <Route index element={<DashboardPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="library" element={<LibraryPage />} />
          <Route path="collections" element={<CollectionsPage />} />
          <Route path="backups" element={<BackupsPage />} />
          <Route path="sources" element={<SourcesPage />} />
          <Route path="display-settings" element={<DisplaySettingsPage />} />
          <Route path="weather" element={<WeatherPage />} />
        </Route>
        <Route path="/" element={<RootRedirect />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ErrorBoundary>
  )
}
