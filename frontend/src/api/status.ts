import { apiGet } from './http'
import { asArray, asBoolean, asNumber, asOptionalString, asRecord, asString, type ImportJobSummary, type SystemStatus } from './types'

export async function getStatus(): Promise<SystemStatus> {
  const payload = await apiGet<unknown>('/api/status')
  const record = asRecord(payload)
  const counts = asRecord(record?.counts)
  const database = asRecord(record?.database)
  const storage = asRecord(record?.storage)
  const activeDisplayProfile = asRecord(record?.active_display_profile)
  const activeCollection = asRecord(record?.active_collection)
  const latestImportJob = asRecord(record?.latest_import_job)

  return {
    ok: asBoolean(record?.ok, true),
    app: asString(record?.app, 'SPF5000'),
    status: asString(record?.status, asBoolean(record?.ok, true) ? 'ready' : 'degraded'),
    hostname: asOptionalString(record?.hostname),
    version: asOptionalString(record?.version),
    asset_count: asNumber(record?.asset_count ?? counts?.assets, 0),
    collection_count: asNumber(record?.collection_count ?? counts?.collections, 0),
    source_count: asNumber(record?.source_count ?? counts?.sources, 0),
    last_sync_at: asOptionalString(record?.last_sync_at) ?? asOptionalString(latestImportJob?.completed_at) ?? null,
    warnings: asArray(record?.warnings, (item) => asString(item)).filter(Boolean),
    database: database
      ? {
          available: asBoolean(database.available, false),
          path: asString(database.path, ''),
          mode: asString(database.mode, ''),
        }
      : undefined,
    storage: storage
      ? {
          data_dir: asString(storage.data_dir, ''),
          originals_dir: asString(storage.originals_dir, ''),
          display_variants_dir: asString(storage.display_variants_dir, ''),
          thumbnails_dir: asString(storage.thumbnails_dir, ''),
          local_import_dir: asString(storage.local_import_dir, ''),
          fallback_asset_url: asString(storage.fallback_asset_url, ''),
        }
      : undefined,
    active_display_profile: activeDisplayProfile
      ? {
          id: asString(activeDisplayProfile.id, ''),
          name: asString(activeDisplayProfile.name, ''),
          selected_collection_id: asOptionalString(activeDisplayProfile.selected_collection_id) ?? null,
          shuffle_enabled: asBoolean(activeDisplayProfile.shuffle_enabled, false),
        }
      : undefined,
    active_collection: activeCollection
      ? {
          id: asString(activeCollection.id, ''),
          name: asString(activeCollection.name, ''),
          asset_count: asNumber(activeCollection.asset_count, 0),
        }
      : null,
    latest_import_job: latestImportJob ? normalizeImportJob(latestImportJob) : null,
  }
}

function normalizeImportJob(record: Record<string, unknown>): ImportJobSummary {
  return {
    id: asString(record.id, ''),
    job_type: asString(record.job_type, 'import'),
    status: asString(record.status, 'unknown'),
    source_id: asOptionalString(record.source_id) ?? null,
    collection_id: asOptionalString(record.collection_id) ?? null,
    import_path: asString(record.import_path, ''),
    discovered_count: asNumber(record.discovered_count, 0),
    imported_count: asNumber(record.imported_count, 0),
    duplicate_count: asNumber(record.duplicate_count, 0),
    skipped_count: asNumber(record.skipped_count, 0),
    error_count: asNumber(record.error_count, 0),
    sample_filenames: [],
    message: asString(record.message, ''),
    started_at: asString(record.started_at, ''),
    completed_at: asOptionalString(record.completed_at) ?? null,
  }
}
