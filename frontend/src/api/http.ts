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
    const message = getErrorMessage(payload, response.status)

    throw new ApiError(message, response.status, payload)
  }

  return payload as T
}

function getErrorMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = payload.detail
    if (typeof detail === 'string') {
      return detail
    }

    if (Array.isArray(detail)) {
      const messages = Array.from(
        new Set(
          detail
            .map((item) => {
              if (!item || typeof item !== 'object') {
                return null
              }

              const messageSource = 'msg' in item ? item.msg : undefined
              const message = typeof messageSource === 'string' ? messageSource : null
              const locationSource = 'loc' in item ? item.loc : undefined
              const location = Array.isArray(locationSource)
                ? locationSource.filter((part: unknown): part is string => typeof part === 'string')
                : []
              const field = location.at(-1)
              if (!message) {
                return null
              }

              return field && field !== 'body' ? `${field}: ${message}` : message
            })
            .filter((message): message is string => Boolean(message)),
        ),
      )

      if (messages.length > 0) {
        return messages.join(' ')
      }
    }
  }

  return `Request failed: ${status}`
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
