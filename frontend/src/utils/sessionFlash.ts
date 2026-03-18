const BACKUP_RESTORE_FLASH_KEY = 'spf5000.backupRestoreFlash'

export function setBackupRestoreFlash(message: string): void {
  try {
    sessionStorage.setItem(BACKUP_RESTORE_FLASH_KEY, message)
  } catch {
    // Ignore storage failures so restore can continue.
  }
}

export function consumeBackupRestoreFlash(): string | null {
  try {
    const message = sessionStorage.getItem(BACKUP_RESTORE_FLASH_KEY)
    if (!message) {
      return null
    }

    sessionStorage.removeItem(BACKUP_RESTORE_FLASH_KEY)
    return message
  } catch {
    return null
  }
}
