import { apiGet, apiPost } from './http'
import {
  asArray,
  asBoolean,
  asOptionalNumber,
  asOptionalString,
  asRecord,
  asString,
  type CreateSourceRequest,
  type SourceSummary,
} from './types'

export async function getSources(): Promise<SourceSummary[]> {
  const payload = await apiGet<unknown>('/api/sources')
  return asArray(payload, normalizeSource)
}

export async function createSource(request: CreateSourceRequest): Promise<SourceSummary> {
  const payload = await apiPost<CreateSourceRequest, unknown>('/api/sources', request)
  return normalizeSource(payload, 0)
}

function normalizeSource(item: unknown, index: number): SourceSummary {
  const record = asRecord(item)

  return {
    id: asOptionalString(record?.id) ?? `${index}`,
    name: asString(record?.name, `Source ${index + 1}`),
    kind: asString(record?.kind, 'local'),
    status: asString(record?.status, 'ready'),
    enabled: asBoolean(record?.enabled, true),
    path: asOptionalString(record?.path),
    asset_count: asOptionalNumber(record?.asset_count),
    last_scan_at: asOptionalString(record?.last_scan_at) ?? null,
    last_import_at: asOptionalString(record?.last_import_at) ?? null,
    detail: asOptionalString(record?.detail),
  }
}
