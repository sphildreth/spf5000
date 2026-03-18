import { apiGet } from './http'
import type { ThemesResponse } from './types'

let cachedThemesResponse: ThemesResponse | null = null
let inflightThemesRequest: Promise<ThemesResponse> | null = null

export async function getThemes(options: { force?: boolean } = {}): Promise<ThemesResponse> {
  if (options.force) {
    cachedThemesResponse = null
    inflightThemesRequest = null
  }

  if (cachedThemesResponse) {
    return cachedThemesResponse
  }

  if (!inflightThemesRequest) {
    inflightThemesRequest = apiGet<ThemesResponse>('/api/themes')
      .then((response) => {
        cachedThemesResponse = response
        return response
      })
      .finally(() => {
        inflightThemesRequest = null
      })
  }

  return inflightThemesRequest
}

export function clearThemesCache(): void {
  cachedThemesResponse = null
  inflightThemesRequest = null
}
