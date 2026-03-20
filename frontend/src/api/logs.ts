import { apiGet } from './http'
import { asArray, asBoolean, asNumber, asOptionalString, asRecord, asString } from './types'

const DEFAULT_LOG_LINE_LIMIT = 300

export interface AdminLogFileSummary {
  name: string
  size_bytes: number
  modified_at: string | null
  is_current: boolean
}

export interface AdminLogsResponse {
  files: AdminLogFileSummary[]
  selected_file: string | null
  line_limit: number
  total_lines: number
  truncated: boolean
  lines: string[]
  fetched_at: string
}

export interface GetAdminLogsOptions {
  file?: string | null
  limit?: number
}

export async function getAdminLogs(options: GetAdminLogsOptions = {}): Promise<AdminLogsResponse> {
  const params = new URLSearchParams()

  const file = typeof options.file === 'string' ? options.file.trim() : ''
  if (file.length > 0) {
    params.set('file', file)
  }

  if (typeof options.limit === 'number' && Number.isFinite(options.limit) && options.limit > 0) {
    params.set('limit', String(Math.trunc(options.limit)))
  }

  const query = params.toString()
  const payload = await apiGet<unknown>(query ? `/api/admin/logs?${query}` : '/api/admin/logs')
  return normalizeAdminLogsResponse(payload)
}

function normalizeAdminLogsResponse(payload: unknown): AdminLogsResponse {
  const record = asRecord(payload)

  return {
    files: asArray(record?.files, normalizeAdminLogFileSummary),
    selected_file: asOptionalString(record?.selected_file) ?? null,
    line_limit: asNumber(record?.line_limit, DEFAULT_LOG_LINE_LIMIT),
    total_lines: asNumber(record?.total_lines, 0),
    truncated: asBoolean(record?.truncated, false),
    lines: asArray(record?.lines, (item) => asString(item, '')),
    fetched_at: asString(record?.fetched_at, new Date().toISOString()),
  }
}

function normalizeAdminLogFileSummary(value: unknown): AdminLogFileSummary {
  const record = asRecord(value)

  return {
    name: asString(record?.name, ''),
    size_bytes: asNumber(record?.size_bytes, 0),
    modified_at: record?.modified_at === null ? null : asOptionalString(record?.modified_at) ?? null,
    is_current: asBoolean(record?.is_current, false),
  }
}
