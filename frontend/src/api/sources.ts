import { apiGet, apiPut } from './http'
import { asArray, asBoolean, asNumber, asOptionalString, asRecord, asString, type SourceSummary, type SourceUpdateRequest } from './types'

export async function getSources(): Promise<SourceSummary[]> {
  const payload = await apiGet<unknown>('/api/sources')
  return asArray(payload, normalizeSource)
}

export async function updateSource(id: string, request: SourceUpdateRequest): Promise<SourceSummary> {
  const payload = await apiPut<SourceUpdateRequest, unknown>(`/api/sources/${id}`, request)
  return normalizeSource(payload, 0)
}

function normalizeSource(item: unknown, index: number): SourceSummary {
  const record = asRecord(item)

  return {
    id: asOptionalString(record?.id) ?? `${index}`,
    name: asString(record?.name, `Source ${index + 1}`),
    provider_type: asString(record?.provider_type, 'local_files'),
    import_path: asString(record?.import_path, ''),
    enabled: asBoolean(record?.enabled, true),
    created_at: asString(record?.created_at, ''),
    updated_at: asString(record?.updated_at, ''),
    last_scan_at: asOptionalString(record?.last_scan_at) ?? null,
    last_import_at: asOptionalString(record?.last_import_at) ?? null,
    asset_count: asNumber(record?.asset_count, 0),
  }
}
