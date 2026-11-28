import { useCallback, useEffect, useRef, useState } from 'react'
import { adminService } from '../services/api'
import Button from './Button'
import RefreshButton from './RefreshButton'

const PAGE_SIZE = 25
const sections = [
  ['overview', 'Overview'],
  ['users', 'Users'],
  ['agents', 'Agents'],
  ['teams', 'Teams'],
  ['runs', 'Run history'],
]

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
  return milliseconds < 1000 ? `${milliseconds} ms` : `${(milliseconds / 1000).toFixed(1)} s`
}

const ownerName = (record) =>
  record.owner_display_name || record.owner_email || (record.owner_id ? `User #${record.owner_id}` : 'Legacy / system')

const AdminDashboard = () => {
  const [section, setSection] = useState('overview')
  const [overview, setOverview] = useState(null)
  const [pageData, setPageData] = useState({ items: [], total: 0, limit: PAGE_SIZE, offset: 0 })
  const [recentRuns, setRecentRuns] = useState([])
  const [offset, setOffset] = useState(0)
  const [searchDraft, setSearchDraft] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedRun, setSelectedRun] = useState(null)
  const [loadingRun, setLoadingRun] = useState(false)
  const [runError, setRunError] = useState('')
  const runDialogRef = useRef(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      if (section === 'overview') {
        const [stats, runs] = await Promise.all([
          adminService.getOverview(),
          adminService.listRuns({ limit: 8 }),
        ])
        setOverview(stats)
        setRecentRuns(runs.items || [])
      } else {
        let response
        if (section === 'users') {
          response = await adminService.listUsers({ limit: PAGE_SIZE, offset, search })
        } else if (section === 'agents') {
          response = await adminService.listAgents({ limit: PAGE_SIZE, offset, search })
        } else if (section === 'teams') {
          response = await adminService.listTeams({ limit: PAGE_SIZE, offset, search })
        } else {
          response = await adminService.listRuns({ limit: PAGE_SIZE, offset, status })
        }
        setPageData(response)
      }
    } catch (requestError) {
      setError(requestError.message || 'Could not load administrator data.')
    } finally {
      setLoading(false)
    }
  }, [offset, search, section, status])

  useEffect(() => {
    void loadData()
  }, [loadData])

  const changeSection = (nextSection) => {
    setSection(nextSection)
    setOffset(0)
    setPageData({ items: [], total: 0, limit: PAGE_SIZE, offset: 0 })
    setSearchDraft('')
    setSearch('')
    setStatus('')
    setError('')
  }

  const submitSearch = (event) => {
    event.preventDefault()
    setOffset(0)
    setSearch(searchDraft.trim())
  }

  const openRun = async (run) => {
    setSelectedRun(run)
    setLoadingRun(true)
    setRunError('')
    try {
      setSelectedRun(await adminService.getRun(run.run_id))
    } catch (requestError) {
      setRunError(requestError.message || 'Could not load run details.')
    } finally {
      setLoadingRun(false)
    }
  }

  const closeRun = useCallback(() => setSelectedRun(null), [])

  useEffect(() => {
    if (!selectedRun) return undefined
    const dialog = runDialogRef.current
    const previouslyFocused = document.activeElement
    const getFocusable = () => [...dialog.querySelectorAll('button:not(:disabled)')]
    getFocusable()[0]?.focus()
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        closeRun()
        return
      }
      if (event.key !== 'Tab') return
      const focusable = getFocusable()
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
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
  }, [closeRun, selectedRun])

  const pageCount = Math.max(1, Math.ceil(pageData.total / PAGE_SIZE))
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div className="page-stack">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="body-copy">Administrator access · account and execution data</p>
        <RefreshButton loading={loading} onClick={() => void loadData()} />
      </div>

      <div className="chat-mode-tabs" role="tablist" aria-label="Administrator sections">
        {sections.map(([id, label]) => (
          <button
            key={id}
            id={`admin-tab-${id}`}
            type="button"
            role="tab"
            aria-selected={section === id}
            aria-controls="admin-panel"
            onClick={() => changeSection(id)}
            className={`mode-button ${section === id ? 'mode-button-active' : ''}`}
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <div className="feedback-error" role="alert">
          <p>{error}</p>
          <Button variant="secondary" size="sm" onClick={() => void loadData()} disabled={loading}>Retry</Button>
        </div>
      )}

      <section id="admin-panel" role="tabpanel" aria-labelledby={`admin-tab-${section}`}>
        {section === 'overview' ? (
          loading && !overview ? (
            <div className="surface table-empty" role="status">Loading administrator overview…</div>
          ) : overview ? (
            <div className="page-stack">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard label="Users" value={overview.users.total} detail={`${overview.users.active} active · ${overview.users.admins} admin`} />
                <StatCard label="Agents" value={overview.agents.total} detail={`${overview.agents.active} active`} />
                <StatCard label="Teams" value={overview.teams.total} detail={`${overview.teams.active} active`} />
                <StatCard label="Runs" value={overview.runs.total} detail={`${overview.runs.total_tokens.toLocaleString()} tokens recorded`} />
              </div>
              <section className="surface overflow-x-auto">
                <div className="border-b border-border px-4 py-3">
                  <h2 className="section-title">Recent runs</h2>
                </div>
                {recentRuns.length === 0 ? (
                  <div className="table-empty">No runs have been recorded.</div>
                ) : (
                  <RunTable runs={recentRuns} onDetails={openRun} compact />
                )}
              </section>
              <section className="surface p-4">
                <h2 className="field-label">Run status</h2>
                <div className="mt-3 flex flex-wrap gap-4 text-sm text-secondary">
                  {Object.entries(overview.runs.by_status).map(([runStatus, count]) => (
                    <span key={runStatus} className="capitalize">{runStatus}: {count}</span>
                  ))}
                  {Object.keys(overview.runs.by_status).length === 0 && <span>No runs yet</span>}
                </div>
              </section>
            </div>
          ) : null
        ) : (
          <div className="page-stack">
            {(section === 'users' || section === 'agents' || section === 'teams') && (
              <form className="flex flex-wrap items-end gap-2" onSubmit={submitSearch}>
                <label className="min-w-56 flex-1">
                  <span className="field-label">Search {section}</span>
                  <input className="input-primary" value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} />
                </label>
                <Button type="submit" variant="secondary">Search</Button>
                {search && <Button variant="ghost" onClick={() => {
                  setSearchDraft('')
                  setSearch('')
                  setOffset(0)
                }}>Clear</Button>}
              </form>
            )}

            {section === 'runs' && (
              <label className="max-w-xs">
                <span className="field-label">Filter by status</span>
                <select className="input-primary" value={status} onChange={(event) => {
                  setStatus(event.target.value)
                  setOffset(0)
                }}>
                  <option value="">All statuses</option>
                  <option value="pending">Pending</option>
                  <option value="running">Running</option>
                  <option value="completed">Completed</option>
                  <option value="error">Error</option>
                </select>
              </label>
            )}

            {loading && pageData.items.length === 0 ? (
              <div className="surface table-empty" role="status">Loading {section}…</div>
            ) : pageData.items.length === 0 ? (
              <section className="empty-state">
                <h2 className="section-title">No {section} found</h2>
                <p className="body-copy">{search || status ? 'Try changing the filters.' : 'There is no data in this section yet.'}</p>
              </section>
            ) : (
              <div className="surface overflow-x-auto">
                {section === 'users' && <UsersTable users={pageData.items} />}
                {section === 'agents' && <AgentsTable agents={pageData.items} />}
                {section === 'teams' && <TeamsTable teams={pageData.items} />}
                {section === 'runs' && <RunTable runs={pageData.items} onDetails={openRun} />}
              </div>
            )}

            <div className="flex items-center justify-between gap-3 text-sm text-secondary">
              <span>{pageData.total.toLocaleString()} total · Page {currentPage} of {pageCount}</span>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))} disabled={loading || offset === 0}>Previous</Button>
                <Button variant="secondary" size="sm" onClick={() => setOffset((value) => value + PAGE_SIZE)} disabled={loading || offset + PAGE_SIZE >= pageData.total}>Next</Button>
              </div>
            </div>
          </div>
        )}
      </section>

      {selectedRun && (
        <div className="modal-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeRun()
        }}>
          <section ref={runDialogRef} className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="admin-run-title">
            <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
              <div className="min-w-0">
                <h2 id="admin-run-title" className="section-title">Run details</h2>
                <p className="mt-1 break-all font-mono text-xs text-muted">{selectedRun.run_id}</p>
              </div>
              <Button variant="secondary" size="sm" onClick={closeRun}>Close</Button>
            </div>
            <div className="grid gap-5 p-5">
              {loadingRun ? <p className="body-copy" role="status">Loading run details…</p> : runError ? (
                <p className="feedback-error" role="alert">{runError}</p>
              ) : (
                <>
                  <dl className="agent-details-grid">
                    <div><dt>Status</dt><dd className="capitalize">{selectedRun.status}</dd></div>
                    <div><dt>Mode</dt><dd className="capitalize">{selectedRun.mode}</dd></div>
                    <div><dt>Owner</dt><dd>{ownerName(selectedRun)}</dd></div>
                    <div><dt>Owner ID</dt><dd>{selectedRun.owner_id ?? 'Legacy / system'}</dd></div>
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
                  <TextBlock title="Prompt" value={selectedRun.prompt} />
                  {selectedRun.output && <TextBlock title="Output" value={selectedRun.output} />}
                  {selectedRun.error && <TextBlock title="Error" value={selectedRun.error} error />}
                </>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

const StatCard = ({ label, value, detail }) => (
  <div className="surface p-4">
    <p className="text-sm text-muted">{label}</p>
    <p className="mt-1 text-2xl font-semibold text-primary">{Number(value || 0).toLocaleString()}</p>
    <p className="mt-1 text-xs text-secondary">{detail}</p>
  </div>
)

const UsersTable = ({ users }) => (
  <table className="agent-table min-w-full">
    <thead><tr>
      <th scope="col">User</th><th scope="col">Email</th><th scope="col">Role</th>
      <th scope="col">Status</th><th scope="col">Runs</th><th scope="col">Joined</th><th scope="col">Last login</th>
    </tr></thead>
    <tbody>{users.map((user) => (
      <tr key={user.user_id}>
        <td>{user.display_name || '—'}</td>
        <td>{user.email}</td>
        <td>{user.is_admin ? 'Administrator' : 'User'}</td>
        <td>{user.is_active ? 'Active' : 'Disabled'}</td>
        <td>{user.run_count ?? 0}</td>
        <td>{formatDate(user.created_at)}</td>
        <td>{formatDate(user.last_login_at)}</td>
      </tr>
    ))}</tbody>
  </table>
)

const AgentsTable = ({ agents }) => (
  <table className="agent-table min-w-full">
    <thead><tr>
      <th scope="col">Agent</th><th scope="col">Type</th><th scope="col">Owner</th>
      <th scope="col">Status</th><th scope="col">Visibility</th><th scope="col">Created</th>
    </tr></thead>
    <tbody>{agents.map((agent) => (
      <tr key={agent.agent_id}>
        <td><span className="agent-name">{agent.name}</span>{agent.description && <p className="agent-description">{agent.description}</p>}</td>
        <td className="capitalize">{agent.kind}</td>
        <td>{ownerName(agent)}</td>
        <td>{agent.is_active ? 'Active' : 'Inactive'}</td>
        <td>{agent.is_public ? 'Public' : 'Private'}</td>
        <td>{formatDate(agent.created_at)}</td>
      </tr>
    ))}</tbody>
  </table>
)

const TeamsTable = ({ teams }) => (
  <table className="agent-table min-w-full">
    <thead><tr>
      <th scope="col">Team</th><th scope="col">Coordinator</th><th scope="col">Members</th>
      <th scope="col">Mode</th><th scope="col">Owner</th><th scope="col">Status</th>
    </tr></thead>
    <tbody>{teams.map((team) => (
      <tr key={team.team_id}>
        <td><span className="agent-name">{team.name}</span>{team.description && <p className="agent-description">{team.description}</p>}</td>
        <td>{team.host_agent_name || `Agent #${team.host_agent_id}`}</td>
        <td title={(team.member_names || []).join(', ')}>{team.member_count}</td>
        <td className="capitalize">{team.mode}</td>
        <td>{ownerName(team)}</td>
        <td>{team.is_active ? 'Active' : 'Inactive'}</td>
      </tr>
    ))}</tbody>
  </table>
)

const RunTable = ({ runs, onDetails, compact = false }) => (
  <table className="agent-table min-w-full">
    <thead><tr>
      <th scope="col">Prompt</th><th scope="col">Status</th><th scope="col">Mode</th>
      {!compact && <th scope="col">Owner</th>}
      <th scope="col">Started</th><th scope="col">Tokens</th><th scope="col"><span className="sr-only">Actions</span></th>
    </tr></thead>
    <tbody>{runs.map((run) => (
      <tr key={run.run_id}>
        <td>
          <span className="agent-name" title={run.prompt_preview || run.prompt}>{run.prompt_preview || run.prompt || 'No prompt'}</span>
          <p className="agent-description font-mono" title={run.run_id}>{run.run_id}</p>
        </td>
        <td className="capitalize">{run.status}</td>
        <td className="capitalize">{run.mode}</td>
        {!compact && <td>{ownerName(run)}</td>}
        <td>{formatDate(run.started_at || run.created_at)}</td>
        <td>{run.total_tokens ?? '—'}</td>
        <td><Button variant="ghost" size="sm" onClick={() => void onDetails(run)}>Details</Button></td>
      </tr>
    ))}</tbody>
  </table>
)

const TextBlock = ({ title, value, error = false }) => (
  <div>
    <h3 className="field-label">{title}</h3>
    <pre className={`${error ? 'feedback-error' : 'surface'} max-h-80 overflow-auto whitespace-pre-wrap p-4 text-sm leading-6`}>{value || '—'}</pre>
  </div>
)

export default AdminDashboard
