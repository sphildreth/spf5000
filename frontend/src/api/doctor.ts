import { apiGet } from './http'
import { asArray, asOptionalString, asRecord, asString, type JsonRecord } from './types'

export type HealthSeverity = 'ok' | 'warning' | 'error' | 'info'

export interface HealthCheck {
  id: string
  title: string
  severity: HealthSeverity
  summary: string
  details: string | null
  remediation: string | null
}

export interface HealthCheckGroup {
  id: string
  title: string
  status: HealthSeverity
  checks: HealthCheck[]
}

export interface DoctorReport {
  overall_status: HealthSeverity
  checked_at: string
  groups: HealthCheckGroup[]
  summary: string
}

export async function getDoctorReport(): Promise<DoctorReport> {
  const payload = await apiGet<unknown>('/api/admin/doctor')
  return normalizeDoctorReport(payload)
}

function normalizeDoctorReport(payload: unknown): DoctorReport {
  const record = asRecord(payload)

  return {
    overall_status: normalizeSeverity(record?.overall_status, 'ok'),
    checked_at: asString(record?.checked_at, new Date().toISOString()),
    groups: asArray(record?.groups, normalizeGroup),
    summary: asString(record?.summary, ''),
  }
}

function normalizeGroup(payload: unknown): HealthCheckGroup {
  const record = asRecord(payload)

  return {
    id: asString(record?.id, ''),
    title: asString(record?.title, ''),
    status: normalizeSeverity(record?.status, 'ok'),
    checks: asArray(record?.checks, normalizeCheck),
  }
}

function normalizeCheck(payload: unknown): HealthCheck {
  const record = asRecord(payload)

  return {
    id: asString(record?.id, ''),
    title: asString(record?.title, ''),
    severity: normalizeSeverity(record?.severity, 'ok'),
    summary: asString(record?.summary, ''),
    details: record?.details === null ? null : asOptionalString(record?.details) ?? null,
    remediation: record?.remediation === null ? null : asOptionalString(record?.remediation) ?? null,
  }
}

function normalizeSeverity(value: unknown, fallback: HealthSeverity): HealthSeverity {
  switch (value) {
    case 'ok':
    case 'warning':
    case 'error':
    case 'info':
      return value
    default:
      return fallback
  }
}
