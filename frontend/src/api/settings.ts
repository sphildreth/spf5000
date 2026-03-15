import { apiGet } from './http'

export function getSettings() {
  return apiGet<{
    slideshow_interval_seconds: number
    transition_mode: string
    fit_mode: string
    shuffle_enabled: boolean
  }>('/api/settings')
}
