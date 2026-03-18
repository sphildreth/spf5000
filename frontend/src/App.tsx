import { Component, Suspense, lazy, type ComponentType, type ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { useSession } from './context/SessionContext'
import { AdminLayout } from './layouts/AdminLayout'

function lazyNamed<TModule extends Record<string, unknown>>(
  loader: () => Promise<TModule>,
  exportName: keyof TModule,
) {
  return lazy(async () => {
    const module = await loader()
    return { default: module[exportName] as ComponentType<any> }
  })
}

const BackupsPage = lazyNamed(() => import('./pages/BackupsPage'), 'BackupsPage')
const CollectionsPage = lazyNamed(() => import('./pages/CollectionsPage'), 'CollectionsPage')
const DashboardPage = lazyNamed(() => import('./pages/DashboardPage'), 'DashboardPage')
const DisplayPage = lazyNamed(() => import('./pages/DisplayPage'), 'DisplayPage')
const DisplaySettingsPage = lazyNamed(() => import('./pages/DisplaySettingsPage'), 'DisplaySettingsPage')
const DoctorPage = lazyNamed(() => import('./pages/DoctorPage'), 'DoctorPage')
const LibraryPage = lazyNamed(() => import('./pages/LibraryPage'), 'LibraryPage')
const LoginPage = lazyNamed(() => import('./pages/LoginPage'), 'LoginPage')
const SetupPage = lazyNamed(() => import('./pages/SetupPage'), 'SetupPage')
const SettingsPage = lazyNamed(() => import('./pages/SettingsPage'), 'SettingsPage')
const SourcesPage = lazyNamed(() => import('./pages/SourcesPage'), 'SourcesPage')
const WeatherPage = lazyNamed(() => import('./pages/WeatherPage'), 'WeatherPage')

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

function RouteSuspense({ children }: { children: ReactNode }) {
  return <Suspense fallback={<LoadingScreen />}>{children}</Suspense>
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
  return <RouteSuspense><SetupPage /></RouteSuspense>
}

function RequireUnauthenticated() {
  const { state } = useSession()
  if (state.status === 'loading') return <LoadingScreen />
  if (!state.bootstrapped) return <Navigate to="/setup" replace />
  if (state.status === 'authenticated') return <Navigate to="/admin" replace />
  return <RouteSuspense><LoginPage /></RouteSuspense>
}

export default function App() {
  return (
      <ErrorBoundary>
      <Routes>
        <Route path="/display" element={<RouteSuspense><DisplayPage /></RouteSuspense>} />
        <Route path="/setup" element={<RequireSetup />} />
        <Route path="/login" element={<RequireUnauthenticated />} />
        <Route path="/admin" element={<RequireAdmin />}>
          <Route index element={<RouteSuspense><DashboardPage /></RouteSuspense>} />
          <Route path="settings" element={<RouteSuspense><SettingsPage /></RouteSuspense>} />
          <Route path="library" element={<RouteSuspense><LibraryPage /></RouteSuspense>} />
          <Route path="collections" element={<RouteSuspense><CollectionsPage /></RouteSuspense>} />
          <Route path="backups" element={<RouteSuspense><BackupsPage /></RouteSuspense>} />
          <Route path="doctor" element={<RouteSuspense><DoctorPage /></RouteSuspense>} />
          <Route path="sources" element={<RouteSuspense><SourcesPage /></RouteSuspense>} />
          <Route path="display-settings" element={<RouteSuspense><DisplaySettingsPage /></RouteSuspense>} />
          <Route path="weather" element={<RouteSuspense><WeatherPage /></RouteSuspense>} />
        </Route>
        <Route path="/" element={<RootRedirect />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ErrorBoundary>
  )
}
