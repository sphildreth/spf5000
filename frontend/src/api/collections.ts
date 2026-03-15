import { apiGet, apiPost, apiPut } from './http'
import {
  asArray,
  asBoolean,
  asOptionalNumber,
  asOptionalString,
  asRecord,
  asString,
  asStringArray,
  type CollectionSummary,
  type CollectionUpsertRequest,
} from './types'

export async function getCollections(): Promise<CollectionSummary[]> {
  const payload = await apiGet<unknown>('/api/collections')
  return asArray(payload, normalizeCollection)
}

export async function createCollection(request: CollectionUpsertRequest): Promise<CollectionSummary> {
  const payload = await apiPost<CollectionUpsertRequest, unknown>('/api/collections', request)
  return normalizeCollection(payload, 0)
}

export async function updateCollection(
  id: string,
  request: CollectionUpsertRequest,
): Promise<CollectionSummary> {
  const payload = await apiPut<CollectionUpsertRequest, unknown>(`/api/collections/${id}`, request)
  return normalizeCollection(payload, 0)
}

function normalizeCollection(item: unknown, index: number): CollectionSummary {
  const record = asRecord(item)

  return {
    id: asOptionalString(record?.id) ?? `${index}`,
    name: asString(record?.name, `Collection ${index + 1}`),
    description: asOptionalString(record?.description),
    asset_count: asOptionalNumber(record?.asset_count),
    source_ids: asStringArray(record?.source_ids),
    updated_at: asOptionalString(record?.updated_at) ?? null,
    is_active: asBoolean(record?.is_active, true),
  }
}
