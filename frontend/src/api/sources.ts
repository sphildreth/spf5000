import { apiGet } from './http'

export function getSources() {
  return apiGet<Array<{ id: string; name: string }>>('/api/sources')
}
