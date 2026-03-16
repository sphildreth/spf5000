export function formatDateTime(value?: string | null): string {
  if (!value) {
    return '—'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function formatNumber(value?: number): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '—'
  }

  return new Intl.NumberFormat().format(value)
}

export function formatBytes(value?: number): string {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
    return '—'
  }
  if (value === 0) {
    return '0 B'
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = value
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }

  return `${new Intl.NumberFormat(undefined, {
    maximumFractionDigits: size >= 10 || unitIndex === 0 ? 0 : 1,
  }).format(size)} ${units[unitIndex]}`
}

export function formatDimensions(width?: number, height?: number): string {
  if (!width || !height) {
    return 'Unknown size'
  }

  return `${width} × ${height}`
}

export function toTitleCase(value: string): string {
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}
