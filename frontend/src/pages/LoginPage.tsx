import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { login } from '../api/auth'
import { ApiError } from '../api/http'
import { useSession } from '../context/SessionContext'

export function LoginPage() {
  const navigate = useNavigate()
  const { state, refresh } = useSession()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const loginUnavailableMessage = !state.authAvailable
    ? state.backendReachable
      ? 'Authentication is unavailable because the backend cannot access DecentDB right now.'
      : 'Authentication is unavailable because the frontend cannot reach the backend API. Start the backend, then refresh this page.'
    : null

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      await login(username, password)
      await refresh()
      navigate('/admin')
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        await refresh()
        navigate('/setup')
        return
      }

      setError(caught instanceof Error ? caught.message : 'Unable to sign in.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <p className="eyebrow">SPF5000</p>
        <h1 className="auth-title">Sign in</h1>
        <p className="auth-desc">Use the local admin account to manage the frame from your LAN.</p>

        {loginUnavailableMessage ? (
          <div className="notice notice--error auth-notice">
            <p>{loginUnavailableMessage}</p>
          </div>
        ) : null}

        {error ? (
          <div className="notice notice--error auth-notice">
            <p>{error}</p>
          </div>
        ) : null}

        <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
          <label className="auth-field">
            <span>Username</span>
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              autoComplete="username"
              autoFocus
            />
          </label>

          <label className="auth-field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              autoComplete="current-password"
            />
          </label>

          <button type="submit" className="button auth-submit" disabled={submitting || !state.authAvailable}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
