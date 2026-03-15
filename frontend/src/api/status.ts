import { apiGet } from './http'
import { asArray, asBoolean, asOptionalNumber, asOptionalString, asRecord, asString, type SystemStatus } from './types'

export async function getStatus(): Promise<SystemStatus> {
  const payload = await apiGet<unknown>('/api/status')
  const record = asRecord(payload)
  const warnings = asArray(record?.warnings, (item) => asString(item)).filter(Boolean)

  return {
    ok: asBoolean(record?.ok, true),
    app: asString(record?.app, 'SPF5000'),
    status: asString(record?.status, asBoolean(record?.ok, true) ? 'ready' : 'degraded'),
    hostname: asOptionalString(record?.hostname),
    version: asOptionalString(record?.version),
    uptime_seconds: asOptionalNumber(record?.uptime_seconds),
    asset_count: asOptionalNumber(record?.asset_count),
    collection_count: asOptionalNumber(record?.collection_count),
    source_count: asOptionalNumber(record?.source_count),
    last_sync_at: asOptionalString(record?.last_sync_at) ?? null,
    warnings,
  }
}
