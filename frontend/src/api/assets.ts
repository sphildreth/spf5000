import { apiDeleteEmpty, apiGet, apiPost, apiPostFormData } from './http'
import {
  asArray,
  asOptionalNumber,
  asOptionalString,
  asRecord,
  asString,
  asStringArray,
  type AssetCollectionBulkDeleteFailure,
  type AssetCollectionBulkDeleteRequest,
  type AssetCollectionBulkDeleteSummary,
  type AssetSummary,
  type AssetUploadSummary,
} from './types'

export async function getAssets(): Promise<AssetSummary[]> {
  const payload = await apiGet<unknown>('/api/assets')
  return asArray(payload, normalizeAsset)
}

export async function uploadAssets(files: File[], collectionId?: string): Promise<AssetUploadSummary> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  if (collectionId) {
    formData.append('collection_id', collectionId)
  }
  const payload = await apiPostFormData<unknown>('/api/assets/upload', formData)
  return normalizeAssetUploadSummary(payload)
}

export async function removeAssetFromCollection(assetId: string, collectionId: string): Promise<void> {
  const params = new URLSearchParams({ collection_id: collectionId })
  await apiDeleteEmpty(`/api/assets/${encodeURIComponent(assetId)}?${params.toString()}`)
}

export async function removeAssetsFromCollection(
  assetIds: string[],
  collectionId: string,
): Promise<AssetCollectionBulkDeleteSummary> {
  const uniqueAssetIds = Array.from(new Set(assetIds.map((assetId) => assetId.trim()).filter(Boolean)))

  if (uniqueAssetIds.length === 0) {
    return {
      removed_count: 0,
      deactivated_count: 0,
      errors: [],
    }
  }

  const request: AssetCollectionBulkDeleteRequest = {
    collection_id: collectionId,
    asset_ids: uniqueAssetIds,
  }
  const payload = await apiPost<AssetCollectionBulkDeleteRequest, unknown>('/api/assets/bulk-remove', request)
  return normalizeAssetCollectionBulkDeleteSummary(payload)
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

function normalizeAssetUploadSummary(item: unknown): AssetUploadSummary {
  const record = asRecord(item)

  return {
    source_id: asString(record?.source_id, ''),
    collection_id: asString(record?.collection_id, ''),
    received_count: asOptionalNumber(record?.received_count) ?? 0,
    imported_count: asOptionalNumber(record?.imported_count) ?? 0,
    duplicate_count: asOptionalNumber(record?.duplicate_count) ?? 0,
    error_count: asOptionalNumber(record?.error_count) ?? 0,
    errors: asStringArray(record?.errors),
  }
}

function normalizeAssetCollectionBulkDeleteSummary(item: unknown): AssetCollectionBulkDeleteSummary {
  const record = asRecord(item)

  return {
    removed_count: asOptionalNumber(record?.removed_count) ?? 0,
    deactivated_count: asOptionalNumber(record?.deactivated_count) ?? 0,
    errors: asArray(record?.errors, normalizeAssetCollectionBulkDeleteFailure),
  }
}

function normalizeAssetCollectionBulkDeleteFailure(item: unknown): AssetCollectionBulkDeleteFailure {
  const record = asRecord(item)

  return {
    asset_id: asString(record?.asset_id, ''),
    reason: asString(record?.reason, 'Could not remove the photo from the collection.'),
  }
}
