import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'

import { getSession, logout as apiLogout } from '../api/auth'
import type { AuthSessionResponse, AuthUser } from '../api/types'

export type SessionStatus = 'loading' | 'anonymous' | 'authenticated'

export interface SessionState {
  status: SessionStatus
  authAvailable: boolean
  backendReachable: boolean
  bootstrapped: boolean
  user: AuthUser | null
}

interface SessionContextValue {
  state: SessionState
  refresh: () => Promise<void>
  logout: () => Promise<void>
}

const SessionContext = createContext<SessionContextValue | null>(null)

function toSessionState(session: AuthSessionResponse): SessionState {
  return {
    status: session.authenticated ? 'authenticated' : 'anonymous',
    authAvailable: session.auth_available,
    backendReachable: true,
    bootstrapped: session.bootstrapped,
    user: session.user,
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>({
    status: 'loading',
    authAvailable: true,
    backendReachable: true,
    bootstrapped: false,
    user: null,
  })

  const refresh = useCallback(async () => {
    try {
      const session = await getSession()
      setState(toSessionState(session))
    } catch {
      setState({
        status: 'anonymous',
        authAvailable: false,
        backendReachable: false,
        bootstrapped: false,
        user: null,
      })
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      const session = await apiLogout()
      setState(toSessionState(session))
    } catch {
      setState((current) => ({
        ...current,
        status: 'anonymous',
        user: null,
      }))
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return <SessionContext.Provider value={{ state, refresh, logout }}>{children}</SessionContext.Provider>
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext)
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider')
  }

  return context
}
