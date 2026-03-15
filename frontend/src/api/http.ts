export class ApiError extends Error {
  readonly status: number
  readonly details?: unknown

  constructor(message: string, status: number, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const hasBody = options.body !== undefined

  if (hasBody && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(path, {
    ...options,
    credentials: 'include',
    headers,
    body: hasBody ? JSON.stringify(options.body) : undefined,
  })

  const text = await response.text()
  const payload = text ? safeParseJson(text) : undefined

  if (!response.ok) {
    const message =
      payload && typeof payload === 'object' && 'detail' in payload && typeof payload.detail === 'string'
        ? payload.detail
        : `Request failed: ${response.status}`

    throw new ApiError(message, response.status, payload)
  }

  return payload as T
}

function safeParseJson(value: string): unknown {
  try {
    return JSON.parse(value) as unknown
  } catch {
    return value
  }
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'GET' })
}

export function apiPost<TRequest, TResponse>(path: string, body: TRequest): Promise<TResponse> {
  return request<TResponse>(path, { method: 'POST', body })
}

export function apiPut<TRequest, TResponse>(path: string, body: TRequest): Promise<TResponse> {
  return request<TResponse>(path, { method: 'PUT', body })
}

export function apiPostEmpty<TResponse>(path: string): Promise<TResponse> {
  return request<TResponse>(path, { method: 'POST' })
}
