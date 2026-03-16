import { apiGet, apiPostEmpty } from './http'
import {
  asArray,
  asBoolean,
  asNumber,
  asOptionalString,
  asRecord,
  asString,
  type GooglePhotosAccountSummary,
  type GooglePhotosDeviceAuthFlow,
  type GooglePhotosDeviceSummary,
  type GooglePhotosMediaSourceSummary,
  type GooglePhotosProviderStatus,
  type GooglePhotosSyncRunSummary,
  type JsonRecord,
} from './types'

export async function getGooglePhotosStatus(): Promise<GooglePhotosProviderStatus> {
  const payload = await apiGet<unknown>('/api/google-photos/status')
  return normalizeGooglePhotosStatus(payload)
}

export async function startGooglePhotosConnect(): Promise<GooglePhotosProviderStatus> {
  const payload = await apiPostEmpty<unknown>('/api/google-photos/connect/start')
  return payload === undefined ? getGooglePhotosStatus() : normalizeGooglePhotosStatus(payload)
}

export async function pollGooglePhotosConnect(): Promise<GooglePhotosProviderStatus> {
  const payload = await apiPostEmpty<unknown>('/api/google-photos/connect/poll')
  return payload === undefined ? getGooglePhotosStatus() : normalizeGooglePhotosStatus(payload)
}

export async function disconnectGooglePhotos(): Promise<GooglePhotosProviderStatus> {
  const payload = await apiPostEmpty<unknown>('/api/google-photos/disconnect')
  return payload === undefined ? getGooglePhotosStatus() : normalizeGooglePhotosStatus(payload)
}

export async function syncGooglePhotos(): Promise<GooglePhotosProviderStatus> {
  const payload = await apiPostEmpty<unknown>('/api/google-photos/sync')
  return payload === undefined ? getGooglePhotosStatus() : normalizeGooglePhotosStatus(payload)
}

function normalizeGooglePhotosStatus(value: unknown): GooglePhotosProviderStatus {
  const record = asRecord(value)
  const providerRecord = asRecord(getValue(record, 'provider'))
  const pendingAuthRecord = asRecord(
    getValue(record, 'pending_auth', 'pendingAuth', 'device_auth_flow', 'deviceAuthFlow'),
  )
  const accountRecord = asRecord(getValue(record, 'account', 'linked_account', 'linkedAccount'))
  const deviceRecord = asRecord(getValue(record, 'device', 'ambient_device', 'ambientDevice'))
  const syncRecord = asRecord(
    getValue(record, 'latest_sync_run', 'latestSyncRun', 'latest_sync', 'latestSync', 'sync_run', 'syncRun'),
  )

  return {
    provider_available: asBoolean(
      getValue(record, 'provider_available', 'providerAvailable') ?? getValue(providerRecord, 'available'),
      false,
    ),
    provider_configured: asBoolean(
      getValue(record, 'provider_configured', 'providerConfigured') ?? getValue(providerRecord, 'configured'),
      false,
    ),
    connection_state: asString(
      getValue(record, 'connection_state', 'connectionState') ??
        getValue(providerRecord, 'connection_state', 'connectionState', 'status'),
      'disconnected',
    ),
    pending_auth: pendingAuthRecord ? normalizePendingAuth(pendingAuthRecord) : null,
    account: accountRecord ? normalizeAccount(accountRecord) : null,
    device: deviceRecord ? normalizeDevice(deviceRecord) : null,
    latest_sync_run: syncRecord ? normalizeSyncRun(syncRecord) : null,
    cached_asset_count: asNumber(getValue(record, 'cached_asset_count', 'cachedAssetCount', 'asset_count'), 0),
    last_successful_sync_at:
      asOptionalString(getValue(record, 'last_successful_sync_at', 'lastSuccessfulSyncAt')) ?? null,
    warning: asOptionalString(getValue(record, 'warning', 'sync_warning', 'syncWarning')) ?? null,
    error: asOptionalString(getValue(record, 'error', 'sync_error', 'syncError')) ?? null,
  }
}

function normalizePendingAuth(record: JsonRecord): GooglePhotosDeviceAuthFlow {
  return {
    user_code: asString(getValue(record, 'user_code', 'userCode'), ''),
    verification_uri: asString(getValue(record, 'verification_uri', 'verificationUri'), ''),
    expires_at: asOptionalString(getValue(record, 'expires_at', 'expiresAt')) ?? null,
    interval_seconds: asNumber(getValue(record, 'interval_seconds', 'intervalSeconds'), 0),
  }
}

function normalizeAccount(record: JsonRecord): GooglePhotosAccountSummary {
  return {
    display_name: asOptionalString(getValue(record, 'display_name', 'displayName', 'name')) ?? null,
    email: asOptionalString(getValue(record, 'email')) ?? null,
    subject: asOptionalString(getValue(record, 'subject', 'sub', 'account_id', 'accountId')) ?? null,
    connected_at: asOptionalString(getValue(record, 'connected_at', 'connectedAt')) ?? null,
  }
}

function normalizeDevice(record: JsonRecord): GooglePhotosDeviceSummary {
  return {
    display_name: asOptionalString(getValue(record, 'display_name', 'displayName', 'name')) ?? null,
    settings_uri: asOptionalString(getValue(record, 'settings_uri', 'settingsUri')) ?? null,
    media_sources_set: asBoolean(getValue(record, 'media_sources_set', 'mediaSourcesSet'), false),
    selected_media_sources: asArray(
      getValue(record, 'selected_media_sources', 'selectedMediaSources', 'media_sources', 'mediaSources'),
      normalizeMediaSource,
    ),
  }
}

function normalizeMediaSource(item: unknown, index: number): GooglePhotosMediaSourceSummary {
  if (typeof item === 'string') {
    return {
      id: item,
      name: item,
      type: null,
    }
  }

  const record = asRecord(item)

  return {
    id: asOptionalString(getValue(record, 'id', 'media_source_id', 'mediaSourceId', 'source_id', 'sourceId')) ?? `${index}`,
    name: asString(getValue(record, 'display_name', 'displayName', 'name', 'title'), `Media source ${index + 1}`),
    type: asOptionalString(getValue(record, 'type', 'kind', 'media_source_type', 'mediaSourceType')) ?? null,
  }
}

function normalizeSyncRun(record: JsonRecord): GooglePhotosSyncRunSummary {
  return {
    id: asOptionalString(getValue(record, 'id')) ?? null,
    status: asString(getValue(record, 'status'), 'unknown'),
    started_at: asOptionalString(getValue(record, 'started_at', 'startedAt')) ?? null,
    completed_at: asOptionalString(getValue(record, 'completed_at', 'completedAt')) ?? null,
    imported_count: asNumber(getValue(record, 'imported_count', 'importedCount'), 0),
    updated_count: asNumber(getValue(record, 'updated_count', 'updatedCount'), 0),
    removed_count: asNumber(getValue(record, 'removed_count', 'removedCount'), 0),
    skipped_count: asNumber(getValue(record, 'skipped_count', 'skippedCount'), 0),
    error_count: asNumber(getValue(record, 'error_count', 'errorCount'), 0),
    message: asOptionalString(getValue(record, 'message', 'detail')) ?? null,
  }
}

function getValue(record: JsonRecord | null, ...keys: string[]): unknown {
  if (!record) {
    return undefined
  }

  for (const key of keys) {
    const value = record[key]
    if (value !== undefined) {
      return value
    }
  }

  return undefined
}
