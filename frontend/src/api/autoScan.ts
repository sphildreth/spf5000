import { apiGet, apiPost } from './http'

export interface AutoScanStatus {
  auto_scan_enabled: boolean
  auto_scan_cron_schedule: string
  auto_watch_enabled: boolean
  auto_watch_debounce_seconds: number
  auto_scan_source_id: string
}

export async function getAutoScanStatus(): Promise<AutoScanStatus> {
  return apiGet('/api/import/auto-scan/status')
}

export async function configureAutoScan(config: Partial<AutoScanStatus>): Promise<AutoScanStatus> {
  return apiPost('/api/import/auto-scan/configure', config)
}
