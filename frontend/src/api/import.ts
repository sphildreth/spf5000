import { apiPost } from './http'
import {
  asArray,
  asNumber,
  asOptionalString,
  asRecord,
  asString,
  type LocalImportRunRequest,
  type LocalImportRunResult,
  type LocalImportScanRequest,
  type LocalImportScanResult,
} from './types'

export async function scanLocalSource(request: LocalImportScanRequest): Promise<LocalImportScanResult> {
  const payload = await apiPost<LocalImportScanRequest, unknown>('/api/import/local/scan', request)
  return normalizeScanResult(payload)
}

export async function runLocalImport(request: LocalImportRunRequest): Promise<LocalImportRunResult> {
  const payload = await apiPost<LocalImportRunRequest, unknown>('/api/import/local/run', request)
  return normalizeRunResult(payload)
}

function normalizeScanResult(payload: unknown): LocalImportScanResult {
  const record = asRecord(payload)

  return {
    discovered_count: asNumber(record?.discovered_count, 0),
    skipped_count: asNumber(record?.skipped_count, 0),
    directories: asArray(record?.directories, (item) => asString(item)).filter(Boolean),
    sample_files: asArray(record?.sample_files, (item) => asString(item)).filter(Boolean),
    warnings: asArray(record?.warnings, (item) => asString(item)).filter(Boolean),
  }
}

function normalizeRunResult(payload: unknown): LocalImportRunResult {
  const record = asRecord(payload)

  return {
    imported_count: asNumber(record?.imported_count, 0),
    duplicate_count: asNumber(record?.duplicate_count, 0),
    failed_count: asNumber(record?.failed_count, 0),
    collection_id: asOptionalString(record?.collection_id),
    warnings: asArray(record?.warnings, (item) => asString(item)).filter(Boolean),
  }
}
