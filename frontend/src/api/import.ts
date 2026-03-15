import { apiPost } from './http'
import { asNumber, asOptionalString, asRecord, asString, asStringArray, type ImportJobSummary, type LocalImportRunRequest, type LocalImportRunResult, type LocalImportScanRequest, type LocalImportScanResult } from './types'

export async function scanLocalSource(request: LocalImportScanRequest): Promise<LocalImportScanResult> {
  const payload = await apiPost<LocalImportScanRequest, unknown>('/api/import/local/scan', request)
  const record = asRecord(payload)

  return {
    job: normalizeImportJob(record?.job),
    import_path: asString(record?.import_path, ''),
    discovered_count: asNumber(record?.discovered_count, 0),
    ignored_count: asNumber(record?.ignored_count, 0),
    sample_filenames: asStringArray(record?.sample_filenames),
  }
}

export async function runLocalImport(request: LocalImportRunRequest): Promise<LocalImportRunResult> {
  const payload = await apiPost<LocalImportRunRequest, unknown>('/api/import/local/run', request)
  return normalizeImportJob(payload)
}

function normalizeImportJob(payload: unknown): ImportJobSummary {
  const record = asRecord(payload)

  return {
    id: asString(record?.id, ''),
    job_type: asString(record?.job_type, 'import'),
    status: asString(record?.status, 'unknown'),
    source_id: asOptionalString(record?.source_id) ?? null,
    collection_id: asOptionalString(record?.collection_id) ?? null,
    import_path: asString(record?.import_path, ''),
    discovered_count: asNumber(record?.discovered_count, 0),
    imported_count: asNumber(record?.imported_count, 0),
    duplicate_count: asNumber(record?.duplicate_count, 0),
    skipped_count: asNumber(record?.skipped_count, 0),
    error_count: asNumber(record?.error_count, 0),
    sample_filenames: asStringArray(record?.sample_filenames),
    message: asString(record?.message, ''),
    started_at: asString(record?.started_at, ''),
    completed_at: asOptionalString(record?.completed_at) ?? null,
  }
}
