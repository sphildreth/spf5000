export type FitMode = 'contain' | 'cover'
export type PlaybackMode = 'shuffle' | 'sequential'

export type JsonRecord = Record<string, unknown>

export interface FrameSettings {
  slideshow_interval_seconds: number
  transition_mode: string
  fit_mode: FitMode
  shuffle_enabled: boolean
}

export interface SystemStatus {
  ok: boolean
  app: string
  status: string
  hostname?: string
  version?: string
  uptime_seconds?: number
  asset_count?: number
  collection_count?: number
  source_count?: number
  last_sync_at?: string | null
  warnings: string[]
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
  created_at?: string | null
  updated_at?: string | null
}

export interface CollectionSummary {
  id: string
  name: string
  description?: string
  asset_count?: number
  source_ids: string[]
  updated_at?: string | null
  is_active: boolean
}

export interface CollectionUpsertRequest {
  name: string
  description?: string
  is_active: boolean
}

export interface SourceSummary {
  id: string
  name: string
  kind: string
  status: string
  enabled: boolean
  path?: string
  asset_count?: number
  last_scan_at?: string | null
  last_import_at?: string | null
  detail?: string
}

export interface CreateSourceRequest {
  name: string
  kind: string
  path: string
}

export interface LocalImportScanRequest {
  path: string
  recursive: boolean
}

export interface LocalImportScanResult {
  discovered_count: number
  skipped_count: number
  directories: string[]
  sample_files: string[]
  warnings: string[]
}

export interface LocalImportRunRequest {
  path: string
  recursive: boolean
  collection_id?: string
}

export interface LocalImportRunResult {
  imported_count: number
  duplicate_count: number
  failed_count: number
  collection_id?: string
  warnings: string[]
}

export interface DisplayConfig {
  interval_seconds: number
  transition_duration_ms: number
  fit_mode: FitMode
  playback_mode: PlaybackMode
  transition_mode: string
  idle_message: string
  refresh_interval_seconds: number
}

export interface DisplayConfigUpdateRequest {
  interval_seconds: number
  transition_duration_ms: number
  fit_mode: FitMode
  playback_mode: PlaybackMode
  transition_mode: string
  idle_message: string
  refresh_interval_seconds: number
}

export interface PlaylistItem {
  id: string
  title: string
  image_url: string
  width?: number
  height?: number
  collection_name?: string
  source_name?: string
}

export interface DisplayPlaylist {
  items: PlaylistItem[]
  revision?: string
  playback_mode?: PlaybackMode
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

export function asPlaybackMode(value: unknown, fallback: PlaybackMode = 'sequential'): PlaybackMode {
  return value === 'shuffle' ? 'shuffle' : fallback
}

export function asOptionalPlaybackMode(value: unknown): PlaybackMode | undefined {
  if (value === 'shuffle' || value === 'sequential') {
    return value
  }
  return undefined
}
