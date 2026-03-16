export type FitMode = 'contain' | 'cover'
export type PlaybackMode = 'shuffle' | 'sequential'

export type JsonRecord = Record<string, unknown>

export interface FrameSettings {
  frame_name: string
  display_variant_width: number
  display_variant_height: number
  thumbnail_max_size: number
  slideshow_interval_seconds: number
  transition_mode: string
  transition_duration_ms: number
  fit_mode: FitMode
  shuffle_enabled: boolean
  selected_collection_id: string
  active_display_profile_id: string
}

export interface ImportJobSummary {
  id: string
  job_type: string
  status: string
  source_id: string | null
  collection_id: string | null
  import_path: string
  discovered_count: number
  imported_count: number
  duplicate_count: number
  skipped_count: number
  error_count: number
  sample_filenames: string[]
  message: string
  started_at: string
  completed_at: string | null
}

export interface SystemStatus {
  ok: boolean
  app: string
  status: string
  hostname?: string
  version?: string
  asset_count: number
  collection_count: number
  source_count: number
  last_sync_at?: string | null
  warnings: string[]
  database?: {
    available: boolean
    path: string
    mode: string
  }
  storage?: {
    data_dir: string
    originals_dir: string
    display_variants_dir: string
    thumbnails_dir: string
    local_import_dir: string
    fallback_asset_url: string
  }
  active_display_profile?: {
    id: string
    name: string
    selected_collection_id: string | null
    shuffle_enabled: boolean
  }
  active_collection?: {
    id: string
    name: string
    asset_count: number
  } | null
  latest_import_job?: ImportJobSummary | null
}

export interface AssetSummary {
  id: string
  title: string
  filename: string
  image_url: string
  thumbnail_url?: string
  width?: number
  height?: number
  mime_type?: string
  source_id?: string
  source_name?: string
  collection_ids: string[]
  collection_names: string[]
  imported_at?: string | null
  updated_at?: string | null
}

export interface AssetUploadSummary {
  source_id: string
  collection_id: string
  received_count: number
  imported_count: number
  duplicate_count: number
  error_count: number
  errors: string[]
}

export interface CollectionSummary {
  id: string
  name: string
  description?: string
  source_id?: string
  source_ids: string[]
  asset_count?: number
  updated_at?: string | null
  is_active: boolean
}

export interface CollectionUpsertRequest {
  name: string
  description?: string
  source_id?: string | null
  is_active: boolean
}

export interface SourceSummary {
  id: string
  name: string
  provider_type: string
  import_path: string
  enabled: boolean
  created_at: string
  updated_at: string
  last_scan_at?: string | null
  last_import_at?: string | null
  asset_count: number
}

export interface SourceUpdateRequest {
  name?: string
  import_path?: string
  enabled?: boolean
}

export interface GooglePhotosDeviceAuthFlow {
  user_code: string
  verification_uri: string
  expires_at: string | null
  interval_seconds: number
}

export interface GooglePhotosAccountSummary {
  display_name: string | null
  email: string | null
  subject: string | null
  connected_at: string | null
}

export interface GooglePhotosMediaSourceSummary {
  id: string
  name: string
  type: string | null
}

export interface GooglePhotosDeviceSummary {
  display_name: string | null
  settings_uri: string | null
  media_sources_set: boolean
  selected_media_sources: GooglePhotosMediaSourceSummary[]
}

export interface GooglePhotosSyncRunSummary {
  id: string | null
  status: string
  started_at: string | null
  completed_at: string | null
  imported_count: number
  updated_count: number
  removed_count: number
  skipped_count: number
  error_count: number
  message: string | null
}

export interface GooglePhotosProviderStatus {
  provider_available: boolean
  provider_configured: boolean
  connection_state: string
  pending_auth: GooglePhotosDeviceAuthFlow | null
  account: GooglePhotosAccountSummary | null
  device: GooglePhotosDeviceSummary | null
  latest_sync_run: GooglePhotosSyncRunSummary | null
  cached_asset_count: number
  last_successful_sync_at: string | null
  warning: string | null
  error: string | null
}

export interface LocalImportScanRequest {
  source_id: string
  max_samples: number
}

export interface LocalImportScanResult {
  job: ImportJobSummary
  import_path: string
  discovered_count: number
  ignored_count: number
  sample_filenames: string[]
}

export interface LocalImportRunRequest {
  source_id: string
  collection_id: string
  max_samples: number
}

export type LocalImportRunResult = ImportJobSummary

export interface DisplayConfig {
  id: string
  name: string
  selected_collection_id: string | null
  slideshow_interval_seconds: number
  transition_mode: string
  transition_duration_ms: number
  fit_mode: FitMode
  shuffle_enabled: boolean
  idle_message: string
  refresh_interval_seconds: number
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface DisplayConfigUpdateRequest {
  name?: string
  selected_collection_id?: string | null
  slideshow_interval_seconds?: number
  transition_mode?: string
  transition_duration_ms?: number
  fit_mode?: FitMode
  shuffle_enabled?: boolean
  idle_message?: string
  refresh_interval_seconds?: number
}

export interface PlaylistItem {
  asset_id: string
  filename: string
  display_url: string
  thumbnail_url: string
  width: number
  height: number
  checksum_sha256: string
  mime_type: string
  collection_name?: string
  source_name?: string
}

export interface SleepSchedule {
  sleep_schedule_enabled: boolean
  sleep_start_local_time: string // HH:MM
  sleep_end_local_time: string // HH:MM
}

export interface SleepScheduleUpdateRequest {
  sleep_schedule_enabled: boolean
  sleep_start_local_time: string // HH:MM
  sleep_end_local_time: string // HH:MM
}

export interface DisplayPlaylist {
  collection_id: string | null
  collection_name: string | null
  shuffle_enabled: boolean
  playlist_revision: string
  profile: DisplayConfig
  items: PlaylistItem[]
  sleep_schedule: SleepSchedule | null
}

export interface AuthUser {
  username: string
}

export interface AuthSessionResponse {
  auth_available: boolean
  bootstrapped: boolean
  authenticated: boolean
  user: AuthUser | null
}

export interface SetupRequest {
  username: string
  password: string
  confirm_password: string
}

export interface LoginRequest {
  username: string
  password: string
}

export function asRecord(value: unknown): JsonRecord | null {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as JsonRecord
  }
  return null
}

export function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

export function asOptionalString(value: unknown): string | undefined {
  return typeof value === 'string' && value.length > 0 ? value : undefined
}

export function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

export function asOptionalNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

export function asBoolean(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback
}

export function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

export function asArray<T>(value: unknown, mapItem: (item: unknown, index: number) => T): T[] {
  if (Array.isArray(value)) {
    return value.map(mapItem)
  }

  const record = asRecord(value)
  const nested = record?.items ?? record?.results ?? record?.data
  return Array.isArray(nested) ? nested.map(mapItem) : []
}

export function asFitMode(value: unknown, fallback: FitMode = 'contain'): FitMode {
  return value === 'cover' ? 'cover' : fallback
}

export function playbackModeFromShuffle(shuffleEnabled: boolean): PlaybackMode {
  return shuffleEnabled ? 'shuffle' : 'sequential'
}

export function normalizeAuthSessionResponse(value: unknown): AuthSessionResponse {
  const record = asRecord(value)
  const userRecord = asRecord(record?.user)
  const username = asOptionalString(userRecord?.username)

  return {
    auth_available: asBoolean(record?.auth_available, true),
    bootstrapped: asBoolean(record?.bootstrapped, false),
    authenticated: asBoolean(record?.authenticated, false),
    user: username ? { username } : null,
  }
}
