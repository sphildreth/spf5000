import { apiPostFormData } from './http'
import type { DatabaseBackupImportResponse } from './types'
import { normalizeDatabaseBackupImportResponse } from './types'

export function getDatabaseBackupExportPath(): string {
  return '/api/backup/database/export'
}

export function getCollectionExportPath(collectionId: string): string {
  return `/api/backup/collections/${encodeURIComponent(collectionId)}/export`
}

export async function importDatabaseBackup(file: File): Promise<DatabaseBackupImportResponse> {
  const formData = new FormData()
  formData.append('archive', file)

  const payload = await apiPostFormData<unknown>('/api/backup/database/import', formData)
  return normalizeDatabaseBackupImportResponse(payload)
}
