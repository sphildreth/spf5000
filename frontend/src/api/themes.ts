import { apiGet } from './http'
import type { ThemesResponse } from './types'

export async function getThemes(): Promise<ThemesResponse> {
  return apiGet<ThemesResponse>('/api/themes')
}
