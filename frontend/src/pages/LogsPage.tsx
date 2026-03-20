import { useEffect, useMemo, useState } from 'react'

import { getAdminLogs, getAdminLogsDownloadUrl, type AdminLogsResponse } from '../api/logs'
import { Card } from '../components/Card'
import { PageHeader } from '../components/PageHeader'
import { StatusNotice } from '../components/StatusNotice'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatBytes, formatDateTime, formatNumber } from '../utils/format'

const LOG_LINE_LIMIT_OPTIONS = [100, 300, 500] as const

type LogLineLimit = (typeof LOG_LINE_LIMIT_OPTIONS)[number]

export function LogsPage() {
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [lineLimit, setLineLimit] = useState<LogLineLimit>(300)
  const { data, loading, error, reload } = useAsyncData<AdminLogsResponse>(
    async () => {
      return await getAdminLogs({ file: selectedFile, limit: lineLimit })
    },
    [selectedFile, lineLimit],
  )

  useEffect(() => {
    if (!data) {
      return
    }

    if (selectedFile && !data.files.some((file) => file.name === selectedFile)) {
      if (data.selected_file !== selectedFile) {
        setSelectedFile(data.selected_file)
      }
    }
  }, [data, selectedFile])

  const selectedLogFile = useMemo(() => {
    if (!data?.selected_file) {
      return null
    }

    return data.files.find((file) => file.name === data.selected_file) ?? null
  }, [data])

  const downloadUrl = useMemo(() => {
    return getAdminLogsDownloadUrl({ file: data?.selected_file ?? selectedFile })
  }, [data?.selected_file, selectedFile])

  const renderedLineStart = useMemo(() => {
    if (!data || data.lines.length === 0) {
      return 1
    }

    return Math.max(data.total_lines - data.lines.length + 1, 1)
  }, [data])

  return (
    <div className="page-stack">
      <PageHeader
        title="Logs"
        description="Inspect recent admin logs without leaving the SPF5000 console. Choose a file, adjust the line limit, and refresh on demand."
        actions={
          <div className="button-row">
            <button type="button" className="button button--ghost" onClick={() => void reload()} disabled={loading}>
              {loading ? 'Refreshing…' : 'Refresh'}
            </button>
            <button
              type="button"
              className="button"
              onClick={() => {
                startLogDownload(downloadUrl)
              }}
              disabled={!data?.selected_file}
            >
              Download file
            </button>
          </div>
        }
      />

      {loading ? <StatusNotice variant="loading" title="Loading log viewer…" /> : null}
      {error ? <StatusNotice variant="error" title="Could not load logs" detail={error} /> : null}

      <div className="two-column-grid">
        <Card title="Viewer controls" eyebrow="Admin logs">
          <div className="form-grid">
            <label>
              <span>Log file</span>
              <select
                value={selectedFile ?? data?.selected_file ?? ''}
                onChange={(event) => setSelectedFile(event.target.value || null)}
                disabled={(data?.files.length ?? 0) === 0}
              >
                {(data?.files ?? []).length === 0 ? (
                  <option value="">No log files available</option>
                ) : null}
                {(data?.files ?? []).map((file) => (
                  <option key={file.name} value={file.name}>
                    {file.is_current ? `${file.name} (current)` : file.name}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span>Line limit</span>
              <select
                value={String(lineLimit)}
                onChange={(event) => setLineLimit(Number(event.target.value) as LogLineLimit)}
              >
                {LOG_LINE_LIMIT_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option} lines
                  </option>
                ))}
              </select>
            </label>

            <dl className="detail-list detail-list--compact logs-meta-list">
              <div>
                <dt>Available files</dt>
                <dd>{formatNumber(data?.files.length ?? 0)}</dd>
              </div>
              <div>
                <dt>Fetched</dt>
                <dd>{formatDateTime(data?.fetched_at)}</dd>
              </div>
            </dl>

            <p className="card-muted">
              This viewer shows a recent slice of server logs returned by <code>/api/admin/logs</code>. There is no live
              streaming; use Refresh whenever you want a fresh snapshot, or Download file to save the full log.
            </p>
          </div>
        </Card>

        <Card title="Selected file" eyebrow="Metadata">
          {selectedLogFile && data ? (
            <>
              <div className="inline-list logs-badges">
                <span className={`pill pill--${selectedLogFile.is_current ? 'ok' : 'muted'}`}>
                  {selectedLogFile.is_current ? 'Current log' : 'Archived log'}
                </span>
                <span className={`pill pill--${data.truncated ? 'warning' : 'ok'}`}>
                  {data.truncated ? 'Truncated view' : 'Full returned view'}
                </span>
              </div>

              <dl className="detail-list logs-meta-list">
                <div>
                  <dt>File name</dt>
                  <dd>{selectedLogFile.name}</dd>
                </div>
                <div>
                  <dt>Size</dt>
                  <dd>{formatBytes(selectedLogFile.size_bytes)}</dd>
                </div>
                <div>
                  <dt>Modified</dt>
                  <dd>{formatDateTime(selectedLogFile.modified_at)}</dd>
                </div>
                <div>
                  <dt>Lines returned</dt>
                  <dd>{formatNumber(data.lines.length)}</dd>
                </div>
                <div>
                  <dt>Total lines</dt>
                  <dd>{formatNumber(data.total_lines)}</dd>
                </div>
                <div>
                  <dt>Line limit</dt>
                  <dd>{formatNumber(data.line_limit)}</dd>
                </div>
              </dl>
            </>
          ) : (data?.files.length ?? 0) === 0 ? (
            <StatusNotice
              variant="empty"
              title="No log files found"
              detail="The backend returned an empty log file list, so there is nothing to inspect yet."
            />
          ) : (
            <StatusNotice
              variant="empty"
              title="No log file selected"
              detail="Choose a file from the selector to inspect recent log lines and metadata."
            />
          )}
        </Card>
      </div>

      {(data?.files.length ?? 0) === 0 ? (
        <StatusNotice
          variant="empty"
          title="No admin logs available"
          detail="When log files exist, they will appear here with a simple read-only snapshot view."
        />
      ) : null}

      {data?.selected_file ? (
        <Card title="Log output" eyebrow={selectedLogFile?.is_current ? 'Current file snapshot' : 'Archived file snapshot'}>
          <p className="card-muted logs-output-summary">
            Showing {formatNumber(data.lines.length)} line{data.lines.length === 1 ? '' : 's'} starting at line{' '}
            {formatNumber(renderedLineStart)} from {data.selected_file}. Fetched {formatDateTime(data.fetched_at)}.
          </p>

          {data.lines.length > 0 ? (
            <div className="logs-panel" role="region" aria-label={`Log lines for ${data.selected_file}`}>
              <ol className="logs-panel-lines" start={renderedLineStart}>
                {data.lines.map((line, index) => (
                  <li key={`${renderedLineStart + index}-${line}`} className="logs-panel-line">
                    <code>{line || ' '}</code>
                  </li>
                ))}
              </ol>
            </div>
          ) : (
            <StatusNotice
              variant="empty"
              title="No log lines returned"
              detail="The selected file exists, but the backend returned an empty line list for this request."
            />
          )}
        </Card>
      ) : null}
    </div>
  )
}

function startLogDownload(path: string) {
  const link = document.createElement('a')
  link.href = path
  link.target = '_blank'
  link.rel = 'noopener noreferrer'
  document.body.append(link)
  link.click()
  link.remove()
}
