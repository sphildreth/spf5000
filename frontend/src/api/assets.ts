import { apiGet } from './http'
import { asArray, asOptionalNumber, asOptionalString, asRecord, asString, asStringArray, type AssetSummary } from './types'

export async function getAssets(): Promise<AssetSummary[]> {
  const payload = await apiGet<unknown>('/api/assets')
  return asArray(payload, normalizeAsset)
}

function normalizeAsset(item: unknown, index: number): AssetSummary {
  const record = asRecord(item)
  const filename = asString(record?.filename, `Asset ${index + 1}`)
  const title = asOptionalString(record?.title) ?? filename

  return {
    id: asOptionalString(record?.id) ?? `${index}`,
    title,
    filename,
    image_url: asString(record?.display_url ?? record?.image_url ?? record?.url, ''),
    thumbnail_url: asOptionalString(record?.thumbnail_url),
    width: asOptionalNumber(record?.width),
    height: asOptionalNumber(record?.height),
    mime_type: asOptionalString(record?.mime_type),
    source_id: asOptionalString(record?.source_id),
    source_name: asOptionalString(record?.source_name),
    collection_ids: asStringArray(record?.collection_ids),
    collection_names: asStringArray(record?.collection_names),
    imported_at: asOptionalString(record?.imported_at) ?? null,
    updated_at: asOptionalString(record?.updated_at) ?? null,
  }
}
