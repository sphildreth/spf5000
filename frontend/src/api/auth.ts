import { apiGet, apiPost, apiPostEmpty } from './http'
import type { AuthSessionResponse, LoginRequest, SetupRequest } from './types'
import { normalizeAuthSessionResponse } from './types'

export async function getSession(): Promise<AuthSessionResponse> {
  const payload = await apiGet<unknown>('/api/auth/session')
  return normalizeAuthSessionResponse(payload)
}

export async function setup(
  username: string,
  password: string,
  confirmPassword: string,
): Promise<AuthSessionResponse> {
  const payload = await apiPost<SetupRequest, unknown>('/api/setup', {
    username,
    password,
    confirm_password: confirmPassword,
  })
  return normalizeAuthSessionResponse(payload)
}

export async function login(username: string, password: string): Promise<AuthSessionResponse> {
  const payload = await apiPost<LoginRequest, unknown>('/api/auth/login', { username, password })
  return normalizeAuthSessionResponse(payload)
}

export async function logout(): Promise<AuthSessionResponse> {
  const payload = await apiPostEmpty<unknown>('/api/auth/logout')
  return normalizeAuthSessionResponse(payload)
}
