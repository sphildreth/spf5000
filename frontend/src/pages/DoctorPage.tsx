import { useCallback } from 'react'

import { getDoctorReport, type DoctorReport, type HealthCheck, type HealthCheckGroup } from '../api/doctor'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatDateTime } from '../utils/format'

function getSeverityLabel(severity: string): string {
  switch (severity) {
    case 'ok':
      return 'Healthy'
    case 'warning':
      return 'Warning'
    case 'error':
      return 'Error'
    case 'info':
      return 'Info'
    default:
      return severity
  }
}

function getSeverityIcon(severity: string): string {
  switch (severity) {
    case 'ok':
      return '\u2713'
    case 'warning':
      return '!'
    case 'error':
      return '\u2717'
    case 'info':
      return 'i'
    default:
      return '?'
  }
}

function getGroupIcon(group: HealthCheckGroup): string {
  const errors = group.checks.filter((c) => c.severity === 'error').length
  const warnings = group.checks.filter((c) => c.severity === 'warning').length

  if (errors > 0) return '\u2717'
  if (warnings > 0) return '!'
  return '\u2713'
}

function HealthCheckRow({ check }: { check: HealthCheck }) {
  return (
    <div className={`doctor-check doctor-check--${check.severity}`}>
      <div className="doctor-check-header">
        <span className={`doctor-check-badge doctor-check-badge--${check.severity}`}>
          {getSeverityIcon(check.severity)}
        </span>
        <span className="doctor-check-title">{check.title}</span>
        <span className={`doctor-check-severity doctor-check-severity--${check.severity}`}>
          {getSeverityLabel(check.severity)}
        </span>
      </div>
      <p className="doctor-check-summary">{check.summary}</p>
      {check.details && <p className="doctor-check-details">{check.details}</p>}
      {check.remediation && (
        <p className="doctor-check-remediation">
          <strong>Fix:</strong> {check.remediation}
        </p>
      )}
    </div>
  )
}

function HealthGroupCard({ group }: { group: HealthCheckGroup }) {
  const errors = group.checks.filter((c) => c.severity === 'error').length
  const warnings = group.checks.filter((c) => c.severity === 'warning').length
  const info = group.checks.filter((c) => c.severity === 'info').length

  return (
    <div className={`doctor-group doctor-group--${group.status}`}>
      <div className="doctor-group-header">
        <span className={`doctor-group-icon doctor-group-icon--${group.status}`}>
          {getGroupIcon(group)}
        </span>
        <h3 className="doctor-group-title">{group.title}</h3>
        <span className="doctor-group-badge-counts">
          {errors > 0 && <span className="pill pill--error">{errors} error{errors !== 1 ? 's' : ''}</span>}
          {warnings > 0 && <span className="pill pill--warning">{warnings} warning{warnings !== 1 ? 's' : ''}</span>}
          {info > 0 && <span className="pill pill--info">{info} info</span>}
        </span>
      </div>
      <div className="doctor-checks">
        {group.checks.map((check) => (
          <HealthCheckRow key={check.id} check={check} />
        ))}
      </div>
    </div>
  )
}

function getVersionsFromReport(report: DoctorReport): { appVersion: string | null; dependencies: string | null } {
  const appGroup = report.groups.find((g) => g.id === 'application')
  if (!appGroup) return { appVersion: null, dependencies: null }

  const versionCheck = appGroup.checks.find((c) => c.id === 'app_version')
  const depsCheck = appGroup.checks.find((c) => c.id === 'dependencies')

  let appVersion: string | null = null
  if (versionCheck) {
    const match = versionCheck.summary.match(/v(\d+\.\d+\.\d+)/)
    appVersion = match ? match[1] : null
  }

  let dependencies: string | null = null
  if (depsCheck && depsCheck.severity !== 'warning') {
    dependencies = depsCheck.summary
  } else if (depsCheck) {
    dependencies = depsCheck.details || depsCheck.summary
  }

  return { appVersion, dependencies }
}

function OverallStatusBadge({
  status,
  summary,
  version,
  dependencies,
}: {
  status: string
  summary: string
  version: string | null
  dependencies: string | null
}) {
  return (
    <div className={`doctor-overall doctor-overall--${status}`}>
      <span className={`doctor-overall-icon doctor-overall-icon--${status}`}>
        {getSeverityIcon(status)}
      </span>
      <div className="doctor-overall-text">
        <span className="doctor-overall-label">System Status</span>
        <span className={`doctor-overall-status doctor-overall-status--${status}`}>
          {getSeverityLabel(status)}
        </span>
        {version && <span className="doctor-overall-version">v{version}</span>}
        {dependencies && <span className="doctor-overall-deps">{dependencies}</span>}
      </div>
      <p className="doctor-overall-summary">{summary}</p>
    </div>
  )
}

export function DoctorPage() {
  const { data, loading, error, reload } = useAsyncData<DoctorReport>(
    async () => {
      return await getDoctorReport()
    },
    [],
  )

  const handleCopyReport = useCallback(() => {
    if (!data) return
    const reportText = generateTextReport(data)
    navigator.clipboard.writeText(reportText)
  }, [data])

  const handleExportJson = useCallback(() => {
    window.location.href = '/api/admin/doctor/export'
  }, [])

  return (
    <div className="page-stack">
      <PageHeader
        title="Doctor"
        description="System health check, troubleshooting, and configuration validation."
        actions={
          <div className="page-header-actions">
            <button
              type="button"
              className="button button--ghost"
              onClick={() => void reload()}
              disabled={loading}
            >
              Refresh
            </button>
            {data && (
              <>
                <button
                  type="button"
                  className="button button--ghost"
                  onClick={() => void handleCopyReport()}
                >
                  Copy Summary
                </button>
                <button
                  type="button"
                  className="button button--ghost"
                  onClick={() => void handleExportJson()}
                >
                  Export JSON
                </button>
              </>
            )}
          </div>
        }
      />

      {loading ? <StatusNotice variant="loading" title="Running health checks..." /> : null}
      {error ? (
        <StatusNotice variant="error" title="Health check failed" detail={error} />
      ) : null}

      {data ? (
        <>
          <OverallStatusBadge
            status={data.overall_status}
            summary={data.summary}
            version={getVersionsFromReport(data).appVersion}
            dependencies={getVersionsFromReport(data).dependencies}
          />

          <p className="doctor-checked-at">
            Last checked: {formatDateTime(data.checked_at)}
          </p>

          <div className="doctor-groups">
            {data.groups.map((group) => (
              <HealthGroupCard key={group.id} group={group} />
            ))}
          </div>
        </>
      ) : null}
    </div>
  )
}

function generateTextReport(report: DoctorReport): string {
  const lines: string[] = [
    `SPF5000 Doctor Report - ${formatDateTime(report.checked_at)}`,
    '='.repeat(60),
    `Overall Status: ${getSeverityLabel(report.overall_status)}`,
    `Summary: ${report.summary}`,
    '',
    'Groups:',
    '-'.repeat(60),
  ]

  for (const group of report.groups) {
    lines.push(`\n[${group.title}] - ${getSeverityLabel(group.status)}`)
    for (const check of group.checks) {
      lines.push(`  ${getSeverityIcon(check.severity)} ${check.title}: ${check.summary}`)
      if (check.remediation) {
        lines.push(`    Fix: ${check.remediation}`)
      }
    }
  }

  return lines.join('\n')
}
