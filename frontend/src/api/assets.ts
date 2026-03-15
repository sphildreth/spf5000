import { apiGet } from './http'
import {
  asArray,
  asOptionalNumber,
  asOptionalString,
  asRecord,
  asStringArray,
  type AssetSummary,
} from './types'

export async function getAssets(): Promise<AssetSummary[]> {
  const payload = await apiGet<unknown>('/api/assets')
  return asArray(payload, normalizeAsset)
}

function normalizeAsset(item: unknown, index: number): AssetSummary {
  const record = asRecord(item)
  const title = asOptionalString(record?.title) ?? asOptionalString(record?.name) ?? `Asset ${index + 1}`
  const filename = asOptionalString(record?.filename) ?? title
  const imageUrl =
    asOptionalString(record?.image_url) ??
    asOptionalString(record?.display_url) ??
    asOptionalString(record?.url) ??
    ''

  return {
    id: asOptionalString(record?.id) ?? `${index}`,
    title,
    filename,
    image_url: imageUrl,
    thumbnail_url:
      asOptionalString(record?.thumbnail_url) ??
      asOptionalString(record?.thumb_url) ??
      asOptionalString(record?.preview_url),
    width: asOptionalNumber(record?.width),
    height: asOptionalNumber(record?.height),
    mime_type: asOptionalString(record?.mime_type),
    source_id: asOptionalString(record?.source_id),
    source_name: asOptionalString(record?.source_name),
    collection_ids: asStringArray(record?.collection_ids),
    collection_names: asStringArray(record?.collection_names),
    created_at: asOptionalString(record?.created_at) ?? null,
    updated_at: asOptionalString(record?.updated_at) ?? null,
  }
}
