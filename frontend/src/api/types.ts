export type FitMode = 'contain' | 'cover'
export type PlaybackMode = 'shuffle' | 'sequential'
export type BackgroundFillMode =
  | 'black'
  | 'dominant_color'
  | 'gradient'
  | 'blurred_backdrop'
  | 'mirrored_edges'
  | 'soft_vignette'
  | 'palette_wash'
  | 'adaptive_auto'
export type DisplayTransitionMode =
  | 'slide'
  | 'slide-right-to-left'
  | 'slide-top-to-bottom'
  | 'slide-bottom-to-top'
  | 'cut'

export type JsonRecord = Record<string, unknown>

const DISPLAY_TRANSITION_MODE_LABELS: Record<DisplayTransitionMode, string> = {
  slide: 'Slide (left to right)',
  'slide-right-to-left': 'Slide (right to left)',
  'slide-top-to-bottom': 'Slide (top to bottom)',
  'slide-bottom-to-top': 'Slide (bottom to top)',
  cut: 'Cut',
}

export const DISPLAY_TRANSITION_MODE_OPTIONS: ReadonlyArray<{
  value: DisplayTransitionMode
  label: string
}> = Object.entries(DISPLAY_TRANSITION_MODE_LABELS).map(([value, label]) => ({
  value: value as DisplayTransitionMode,
  label,
}))

export function asDisplayTransitionMode(
  value: unknown,
  fallback: DisplayTransitionMode = 'slide',
): DisplayTransitionMode {
  switch (value) {
    case 'slide':
    case 'slide-right-to-left':
    case 'slide-top-to-bottom':
    case 'slide-bottom-to-top':
    case 'cut':
      return value
    default:
      return fallback
  }
}

export function getDisplayTransitionModeLabel(value: DisplayTransitionMode): string {
  return DISPLAY_TRANSITION_MODE_LABELS[value]
}

const BACKGROUND_FILL_MODE_LABELS: Record<BackgroundFillMode, string> = {
  black: 'Black',
  dominant_color: 'Dominant Color',
  gradient: 'Gradient',
  blurred_backdrop: 'Blurred Backdrop',
  mirrored_edges: 'Mirrored Edges',
  soft_vignette: 'Soft Vignette',
  palette_wash: 'Palette Wash',
  adaptive_auto: 'Adaptive Auto',
}

const BACKGROUND_FILL_MODE_DESCRIPTIONS: Record<BackgroundFillMode, string> = {
  black: 'Leaves unused screen space solid black.',
  dominant_color: 'Uses a subdued color sampled from the current photo.',
  gradient: 'Builds a calm gradient from colors sampled from the current photo.',
  blurred_backdrop: 'Places a blurred, dimmed version of the photo behind the main image.',
  mirrored_edges: 'Extends mirrored image edges outward so portrait shots feel less boxed in.',
  soft_vignette: 'Adds a gentle image-derived fill with darker edges to keep focus on the photo.',
  palette_wash: 'Applies a soft multi-color wash derived from the photo palette.',
  adaptive_auto: 'Automatically picks the best background treatment for each photo based on its shape and available image colors.',
}

export const BACKGROUND_FILL_MODE_OPTIONS: ReadonlyArray<{
  value: BackgroundFillMode
  label: string
}> = Object.entries(BACKGROUND_FILL_MODE_LABELS).map(([value, label]) => ({
  value: value as BackgroundFillMode,
  label,
}))

export function asBackgroundFillMode(value: unknown, fallback: BackgroundFillMode = 'black'): BackgroundFillMode {
  switch (value) {
    case 'black':
    case 'dominant_color':
    case 'gradient':
    case 'blurred_backdrop':
    case 'mirrored_edges':
    case 'soft_vignette':
    case 'palette_wash':
    case 'adaptive_auto':
      return value
    default:
      return fallback
  }
}

export function getBackgroundFillModeLabel(value: BackgroundFillMode): string {
  return BACKGROUND_FILL_MODE_LABELS[value]
}

export function getBackgroundFillModeDescription(value: BackgroundFillMode): string {
  return BACKGROUND_FILL_MODE_DESCRIPTIONS[value]
}

export interface FrameSettings {
  frame_name: string
  display_variant_width: number
  display_variant_height: number
  thumbnail_max_size: number
  theme_id: string
  home_city_accent_style: string
  slideshow_interval_seconds: number
  transition_mode: DisplayTransitionMode
  transition_duration_ms: number
  fit_mode: FitMode
  shuffle_enabled: boolean
  shuffle_bag_enabled: boolean
  selected_collection_id: string
  active_display_profile_id: string
  background_fill_mode: BackgroundFillMode
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

export interface AssetCollectionBulkDeleteRequest {
  collection_id: string
  asset_ids: string[]
}

export interface AssetCollectionBulkDeleteFailure {
  asset_id: string
  reason: string
}

export interface AssetCollectionBulkDeleteSummary {
  removed_count: number
  deactivated_count: number
  errors: AssetCollectionBulkDeleteFailure[]
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

export interface DatabaseBackupImportResponse {
  restored: boolean
  reauthenticate_required: boolean
  media_restored: boolean
  message: string
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
  transition_mode: DisplayTransitionMode
  transition_duration_ms: number
  fit_mode: FitMode
  shuffle_enabled: boolean
  shuffle_bag_enabled: boolean
  idle_message: string
  refresh_interval_seconds: number
  background_fill_mode: BackgroundFillMode
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface DisplayConfigUpdateRequest {
  name?: string
  selected_collection_id?: string | null
  slideshow_interval_seconds?: number
  transition_mode?: DisplayTransitionMode
  transition_duration_ms?: number
  fit_mode?: FitMode
  shuffle_enabled?: boolean
  shuffle_bag_enabled?: boolean
  idle_message?: string
  refresh_interval_seconds?: number
  background_fill_mode?: BackgroundFillMode
}

export interface PlaylistItemBackground {
  ready: boolean
  dominant_color: string | null
  gradient_colors: string[] | null
}

export interface PlaylistItem {
  asset_id: string
  filename: string
  display_url: string
  thumbnail_url: string
  width: number
  height: number
  checksum_sha256?: string
  mime_type: string
  collection_name?: string
  source_name?: string
  background: PlaylistItemBackground | null
}

export interface SleepSchedule {
  sleep_schedule_enabled: boolean
  sleep_start_local_time: string // HH:MM
  sleep_end_local_time: string // HH:MM
  display_timezone: string | null
}

export interface SleepScheduleUpdateRequest {
  sleep_schedule_enabled: boolean
  sleep_start_local_time: string // HH:MM
  sleep_end_local_time: string // HH:MM
  display_timezone: string | null
}

export interface SettingsTimeReference {
  current_server_utc_timestamp: string
  pi_local_timezone: string
  configured_display_timezone: string | null
  effective_display_timezone: string
  available_timezones: string[]
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

export interface WeatherLocation {
  label: string
  latitude: number | null
  longitude: number | null
}

export interface WeatherSettings {
  weather_enabled: boolean
  weather_provider: string
  weather_location: WeatherLocation
  weather_units: 'f' | 'c'
  weather_position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
  weather_refresh_minutes: number
  weather_show_precipitation: boolean
  weather_show_humidity: boolean
  weather_show_wind: boolean
  weather_alerts_enabled: boolean
  weather_alert_fullscreen_enabled: boolean
  weather_alert_minimum_severity: 'unknown' | 'minor' | 'moderate' | 'severe' | 'extreme'
  weather_alert_repeat_enabled: boolean
  weather_alert_repeat_interval_minutes: number
  weather_alert_repeat_display_seconds: number
}

export interface WeatherProviderState {
  provider_name: string
  provider_display_name: string
  status: string
  available: boolean
  configured: boolean
  location_label: string
  last_weather_refresh_at: string | null
  last_alert_refresh_at: string | null
  last_successful_weather_refresh_at: string | null
  last_successful_alert_refresh_at: string | null
  current_error: string | null
  updated_at: string
}

export interface WeatherCurrentConditions {
  provider_name: string
  provider_display_name: string
  location_label: string
  condition: string
  icon_token: string
  temperature: number | null
  temperature_unit: string
  humidity_percent: number | null
  wind_speed: number | null
  wind_unit: string
  wind_direction: string | null
  precipitation_probability_percent: number | null
  observed_at: string | null
  fetched_at: string
  attribution: string
  is_stale: boolean
}

export interface WeatherAlert {
  id: string
  provider_name: string
  provider_display_name: string
  event: string
  severity: string
  certainty: string
  urgency: string
  headline: string
  description: string
  instruction: string
  area: string
  status: string
  issued_at: string | null
  effective_at: string | null
  expires_at: string | null
  ends_at: string | null
  attribution: string
  escalation_mode: string
  effective_escalation_mode: string
  display_priority: number
  effective_display_priority: number
  event_priority: number
  is_active: boolean
  is_dominant: boolean
}

export interface WeatherRefreshRun {
  id: string
  provider_name: string
  refresh_kind: string
  trigger: string
  status: string
  message: string
  error_message: string | null
  started_at: string
  completed_at: string | null
}

export interface WeatherStatus {
  provider_status: WeatherProviderState
  current_conditions: WeatherCurrentConditions | null
  dominant_alert: WeatherAlert | null
  active_alert_count: number
  current_display_action: string
  recent_refresh_runs: WeatherRefreshRun[]
}

export interface WeatherAlertsState {
  provider_status: WeatherProviderState
  alert_count: number
  dominant_alert: WeatherAlert | null
  active_alerts: WeatherAlert[]
}

export interface DisplayWeather {
  enabled: boolean
  position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
  units: 'f' | 'c'
  show_precipitation: boolean
  show_humidity: boolean
  show_wind: boolean
  provider_status: WeatherProviderState
  current_conditions: WeatherCurrentConditions | null
}

export interface DisplayAlertPresentation {
  mode: string
  fallback_mode: string | null
  repeat_interval_minutes: number
  repeat_display_seconds: number
  alert_count: number
}

export interface DisplayAlerts {
  provider_status: WeatherProviderState
  dominant_alert: WeatherAlert | null
  active_alerts: WeatherAlert[]
  presentation: DisplayAlertPresentation
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

export function normalizeDatabaseBackupImportResponse(value: unknown): DatabaseBackupImportResponse {
  const record = asRecord(value)

  return {
    restored: asBoolean(record?.restored, true),
    reauthenticate_required: asBoolean(record?.reauthenticate_required ?? record?.requires_relogin, true),
    media_restored: asBoolean(record?.media_restored, false),
    message: asString(record?.message, 'Database backup restored. Sign in again to continue.'),
  }
}

// ─── Theme System ──────────────────────────────────────────────────────────

export interface ThemeTokens {
  colors: Record<string, string>
  typography: Record<string, string>
  spacing: Record<string, string>
  motion: Record<string, string>
  shape: Record<string, string>
}

export interface ThemeDefinition {
  id: string
  name: string
  description: string
  version: string
  mode: string
  tokens: ThemeTokens
  components: JsonRecord
  contexts: JsonRecord
}

export interface ThemesResponse {
  active_theme_id: string
  home_city_accent_style: string
  themes: ThemeDefinition[]
}
