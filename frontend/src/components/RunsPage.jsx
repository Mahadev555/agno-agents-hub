import { useCallback, useEffect, useRef, useState } from 'react'
import { runService } from '../services/api'
import Button from './Button'
import RefreshButton from './RefreshButton'

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
})

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isFinite(date.getTime()) ? dateFormatter.format(date) : '—'
}

const formatDuration = (milliseconds) => {
  if (!Number.isFinite(milliseconds)) return '—'
  if (milliseconds < 1000) return `${milliseconds} ms`
  return `${(milliseconds / 1000).toFixed(1)} s`
}

const RunsPage = () => {
  const [runs, setRuns] = useState([])
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedRun, setSelectedRun] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [detailError, setDetailError] = useState('')
  const detailDialogRef = useRef(null)

  const loadRuns = useCallback(async () => {
    setError('')
    try {
      const recentRuns = await runService.list(100, statusFilter || null)
      setRuns(Array.isArray(recentRuns) ? recentRuns : [])
      return true
    } catch (requestError) {
      setError(requestError.message || 'Could not load run history.')
      return false
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    setLoading(true)
    void loadRuns()
  }, [loadRuns])

  useEffect(() => {
    if (!runs.some((run) => run.status === 'pending' || run.status === 'running')) return undefined
    const timer = window.setInterval(() => void loadRuns(), 5000)
    return () => window.clearInterval(timer)
  }, [loadRuns, runs])

  const closeDetails = useCallback(() => setSelectedRun(null), [])

  useEffect(() => {
    if (!selectedRun) return undefined
    const dialog = detailDialogRef.current
    const previouslyFocused = document.activeElement
    const focusable = () => [...dialog.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)')]
    const initialFocus = dialog.querySelector('[data-dialog-initial-focus]') || focusable()[0]
    initialFocus?.focus()
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        closeDetails()
        return
      }
      if (event.key !== 'Tab') return
      const items = focusable()
      if (items.length === 0) return
      const first = items[0]
      const last = items[items.length - 1]
      if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) {
        event.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      previouslyFocused?.focus?.()
    }
  }, [closeDetails, selectedRun])

  const openRun = async (run) => {
    setSelectedRun(run)
    setLoadingDetail(true)
    setDetailError('')
    try {
      setSelectedRun(await runService.get(run.run_id))
    } catch (requestError) {
      setDetailError(requestError.message || 'Could not load run details.')
    } finally {
      setLoadingDetail(false)
    }
  }

  return (
    <div className="page-stack">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <label className="min-w-48">
          <span className="field-label">Status</span>
          <select className="input-primary" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="">All runs</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="error">Error</option>
          </select>
        </label>
        <RefreshButton loading={loading} onClick={() => void loadRuns()} />
      </div>

      {error && (
        <div className="feedback-error" role="alert">
          <p>{error}</p>
          <Button variant="secondary" size="sm" onClick={() => void loadRuns()} disabled={loading}>Retry</Button>
        </div>
      )}

      {loading && runs.length === 0 ? (
        <div className="surface table-empty" role="status">Loading run history…</div>
      ) : runs.length === 0 && !error ? (
        <section className="empty-state">
          <h2 className="section-title">No runs found</h2>
          <p className="body-copy">{statusFilter ? `There are no ${statusFilter} runs.` : 'Run an agent or saved team to see its execution history here.'}</p>
        </section>
      ) : runs.length > 0 ? (
        <div className="surface overflow-x-auto">
          <table className="agent-table min-w-full">
            <thead>
              <tr>
                <th scope="col">Prompt</th>
                <th scope="col">Status</th>
                <th scope="col">Mode</th>
                <th scope="col">Started</th>
                <th scope="col">Duration</th>
                <th scope="col">Tokens</th>
                <th scope="col"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.run_id}>
                  <td>
                    <span className="agent-name" title={run.prompt}>{run.prompt || 'No prompt'}</span>
                    <p className="agent-description font-mono" title={run.run_id}>{run.run_id}</p>
                  </td>
                  <td><span className="capitalize">{run.status}</span></td>
                  <td className="capitalize">{run.mode || '—'}</td>
                  <td><time dateTime={run.started_at || run.created_at}>{formatDate(run.started_at || run.created_at)}</time></td>
                  <td>{formatDuration(run.duration_ms)}</td>
                  <td>{run.total_tokens ?? '—'}</td>
                  <td>
                    <Button variant="ghost" size="sm" onClick={() => void openRun(run)}>Details</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {selectedRun && (
        <div className="modal-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeDetails()
        }}>
          <section ref={detailDialogRef} className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="run-details-title">
            <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
              <div className="min-w-0">
                <h2 id="run-details-title" className="section-title">Run details</h2>
                <p className="mt-1 break-all font-mono text-xs text-muted">{selectedRun.run_id}</p>
              </div>
              <Button variant="secondary" size="sm" data-dialog-initial-focus onClick={closeDetails}>Close</Button>
            </div>
            <div className="grid gap-5 p-5">
              {loadingDetail ? (
                <p className="body-copy" role="status">Loading run details…</p>
              ) : detailError ? (
                <p className="feedback-error" role="alert">{detailError}</p>
              ) : (
                <>
                  <dl className="agent-details-grid">
                    <div><dt>Status</dt><dd className="capitalize">{selectedRun.status}</dd></div>
                    <div><dt>Mode</dt><dd className="capitalize">{selectedRun.mode || '—'}</dd></div>
                    <div><dt>Created</dt><dd>{formatDate(selectedRun.created_at)}</dd></div>
                    <div><dt>Started</dt><dd>{formatDate(selectedRun.started_at)}</dd></div>
                    <div><dt>Finished</dt><dd>{formatDate(selectedRun.finished_at)}</dd></div>
                    <div><dt>Duration</dt><dd>{formatDuration(selectedRun.duration_ms)}</dd></div>
                    <div><dt>Input tokens</dt><dd>{selectedRun.input_tokens ?? '—'}</dd></div>
                    <div><dt>Output tokens</dt><dd>{selectedRun.output_tokens ?? '—'}</dd></div>
                    <div><dt>Total tokens</dt><dd>{selectedRun.total_tokens ?? '—'}</dd></div>
                    <div><dt>Coordinator ID</dt><dd>{selectedRun.host_agent_id ?? '—'}</dd></div>
                    <div className="sm:col-span-2"><dt>Agent IDs</dt><dd className="font-mono">{(selectedRun.agent_ids || []).join(', ') || '—'}</dd></div>
                  </dl>
                  <div>
                    <h3 className="field-label">Prompt</h3>
                    <pre className="surface max-h-48 overflow-auto whitespace-pre-wrap p-4 text-sm leading-6">{selectedRun.prompt || '—'}</pre>
                  </div>
                  {selectedRun.output && (
                    <div>
                      <h3 className="field-label">Output</h3>
                      <pre className="surface max-h-80 overflow-auto whitespace-pre-wrap p-4 text-sm leading-6">{selectedRun.output}</pre>
                    </div>
                  )}
                  {selectedRun.error && (
                    <div>
                      <h3 className="field-label">Error</h3>
                      <pre className="feedback-error whitespace-pre-wrap">{selectedRun.error}</pre>
                    </div>
                  )}
                </>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default RunsPage
