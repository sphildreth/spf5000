import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { setup } from '../api/auth'
import { ApiError } from '../api/http'
import { useSession } from '../context/SessionContext'

export function SetupPage() {
  const navigate = useNavigate()
  const { state, refresh } = useSession()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setSubmitting(true)

    try {
      await setup(username, password, confirmPassword)
      await refresh()
      navigate('/admin')
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        await refresh()
        navigate('/login')
        return
      }

      setError(caught instanceof Error ? caught.message : 'Unable to complete setup.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <p className="eyebrow">SPF5000</p>
        <h1 className="auth-title">Set up the admin account</h1>
        <p className="auth-desc">This one-time step creates the local admin user for the frame.</p>

        {!state.authAvailable ? (
          <div className="notice notice--error auth-notice">
            <p>Setup is unavailable because the backend cannot access DecentDB right now.</p>
          </div>
        ) : null}

        {error ? (
          <div className="notice notice--error auth-notice">
            <p>{error}</p>
          </div>
        ) : null}

        <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
          <label className="auth-field">
            <span>Admin username</span>
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
              autoComplete="new-password"
            />
          </label>

          <label className="auth-field">
            <span>Confirm password</span>
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
              autoComplete="new-password"
            />
          </label>

          <button type="submit" className="button auth-submit" disabled={submitting || !state.authAvailable}>
            {submitting ? 'Creating admin…' : 'Create admin'}
          </button>
        </form>
      </div>
    </div>
  )
}
