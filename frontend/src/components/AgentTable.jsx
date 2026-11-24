import { useMemo, useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import Button from './Button'
import { AGENT_TYPES, getAgentType, getAgentTypeLabel } from '../services/agentTypes'

const relativeTimeFormatter = new Intl.RelativeTimeFormat(undefined, {
  numeric: 'auto',
  style: 'narrow',
})
const absoluteTimeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
})
const timeUnits = [
  ['year', 365.25 * 24 * 60 * 60 * 1000],
  ['month', 30.44 * 24 * 60 * 60 * 1000],
  ['week', 7 * 24 * 60 * 60 * 1000],
  ['day', 24 * 60 * 60 * 1000],
  ['hour', 60 * 60 * 1000],
  ['minute', 60 * 1000],
  ['second', 1000],
]

const getModel = (agent) =>
  agent.config?.model_config?.id ||
  agent.config?.model?.id ||
  agent.config?.model_id ||
  '—'

const getRunTimestamp = (agent, lastRuns) =>
  lastRuns[String(agent.agent_id || agent.id)] || agent.last_run_at || null

const getTimestampValue = (agent, lastRuns) => {
  const timestamp = getRunTimestamp(agent, lastRuns)
  const value = timestamp ? Date.parse(timestamp) : Number.NaN
  return Number.isFinite(value) ? value : null
}

const getRelativeTime = (timestamp) => {
  const date = new Date(timestamp)
  if (!Number.isFinite(date.getTime())) return null

  const difference = date.getTime() - Date.now()
  const [unit, unitLength] = timeUnits.find(([, length]) => Math.abs(difference) >= length)
    || timeUnits[timeUnits.length - 1]
  return {
    date,
    text: relativeTimeFormatter.format(Math.round(difference / unitLength), unit),
  }
}

const Status = ({ active }) => (
  <span className="status-text">
    <span className={`status-dot ${active ? '' : 'status-dot-inactive'}`} aria-hidden="true" />
    {active ? 'Active' : 'Inactive'}
  </span>
)

const RunButton = ({ agent, onRun }) => {
  const id = agent.agent_id || agent.id
  const active = agent.is_active !== false
  const coordinator = getAgentType(agent) === AGENT_TYPES.COORDINATOR
  return (
    <Button
      variant="ghost"
      size="sm"
      className="button-run"
      disabled={!active}
      onClick={() => onRun?.(id, coordinator)}
      aria-label={`Run ${agent.name}`}
    >
      Run
    </Button>
  )
}

const LastRun = ({ agent, lastRuns }) => {
  const timestamp = getRunTimestamp(agent, lastRuns)
  if (!timestamp) return <span>Never</span>

  const formatted = getRelativeTime(timestamp)
  if (!formatted) return <span>Never</span>

  const absolute = absoluteTimeFormatter.format(formatted.date)
  return (
    <time dateTime={formatted.date.toISOString()} title={absolute}>
      {formatted.text}
    </time>
  )
}

const SortButton = ({ label, sortKey, sort, onSort }) => {
  const active = sort.key === sortKey
  const Icon = sort.direction === 'asc' ? ChevronUp : ChevronDown
  return (
    <button
      type="button"
      className="table-sort-button"
      onClick={() => onSort(sortKey)}
      aria-label={`Sort by ${label}${active ? `, ${sort.direction === 'asc' ? 'ascending' : 'descending'}` : ''}`}
      aria-pressed={active}
    >
      {label}
      {active && <Icon size={14} strokeWidth={1.5} aria-hidden="true" />}
    </button>
  )
}

const openDetailsForRow = (event, agent, onDetails) => {
  if (event.target instanceof Element && event.target.closest('button, a, input, select, textarea')) return
  onDetails?.(agent)
}

const handleRowKeyDown = (event, agent, onDetails) => {
  if (event.target !== event.currentTarget || (event.key !== 'Enter' && event.key !== ' ')) return
  event.preventDefault()
  onDetails?.(agent)
}

const AgentTable = ({
  agents,
  lastRuns = {},
  onRun,
  onDetails,
  limit,
  initialSort = 'name',
  initialDirection = 'asc',
}) => {
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState({ key: initialSort, direction: initialDirection })

  const visibleAgents = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase()
    const filtered = agents.filter((agent) =>
      (agent.name || '').toLocaleLowerCase().includes(normalizedQuery)
    )
    const ordered = [...filtered].sort((a, b) => {
      if (sort.key === 'lastRun') {
        const aTime = getTimestampValue(a, lastRuns)
        const bTime = getTimestampValue(b, lastRuns)
        if (aTime === null) return bTime === null ? 0 : 1
        if (bTime === null) return -1
        return (aTime - bTime) * (sort.direction === 'asc' ? 1 : -1)
      }

      const comparison = (a.name || '').localeCompare(b.name || '', undefined, {
        sensitivity: 'base',
        numeric: true,
      })
      return comparison * (sort.direction === 'asc' ? 1 : -1)
    })
    return typeof limit === 'number' ? ordered.slice(0, limit) : ordered
  }, [agents, lastRuns, limit, query, sort])

  const showStatus = new Set(visibleAgents.map((agent) => agent.is_active !== false)).size > 1
  const tableClassName = `agent-table agent-table-desktop ${showStatus ? 'agent-table-has-status' : 'agent-table-no-status'}`
  const ariaSort = (key) => (
    sort.key === key ? (sort.direction === 'asc' ? 'ascending' : 'descending') : undefined
  )
  const toggleSort = (key) => {
    setSort((current) => ({
      key,
      direction: current.key === key && current.direction === 'asc' ? 'desc' : 'asc',
    }))
  }

  return (
    <div className="agent-table-section">
      <div className="table-toolbar">
        <label className="table-search">
          <span className="sr-only">Search agents by name</span>
          <input
            type="search"
            className="input-primary"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search agents"
            autoComplete="off"
          />
        </label>
      </div>

      {visibleAgents.length === 0 ? (
        <div className="table-empty" role="status">
          No agents match this search.
        </div>
      ) : (
        <div className="agent-table-wrap">
          <table className={tableClassName}>
            <thead>
              <tr>
                <th scope="col" aria-sort={ariaSort('name')}>
                  <SortButton label="Name" sortKey="name" sort={sort} onSort={toggleSort} />
                </th>
                {showStatus && <th scope="col">Status</th>}
                <th scope="col">Type</th>
                <th scope="col">Model</th>
                <th scope="col" aria-sort={ariaSort('lastRun')}>
                  <SortButton label="Last run" sortKey="lastRun" sort={sort} onSort={toggleSort} />
                </th>
                <th scope="col"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {visibleAgents.map((agent) => {
                const id = agent.agent_id || agent.id
                const active = agent.is_active !== false
                return (
                  <tr
                    key={id}
                    tabIndex={0}
                    aria-label={`Agent ${agent.name}. Press Enter for details.`}
                    onClick={(event) => openDetailsForRow(event, agent, onDetails)}
                    onKeyDown={(event) => handleRowKeyDown(event, agent, onDetails)}
                  >
                    <td>
                      <span className="agent-name">{agent.name}</span>
                      {agent.description && (
                        <p className="agent-description" title={agent.description}>
                          {agent.description}
                        </p>
                      )}
                    </td>
                    {showStatus && <td><Status active={active} /></td>}
                    <td className="text-13">{getAgentTypeLabel(agent)}</td>
                    <td className="font-mono text-xs">{getModel(agent)}</td>
                    <td className="text-13"><LastRun agent={agent} lastRuns={lastRuns} /></td>
                    <td>
                      <div className="table-actions">
                        <RunButton agent={agent} onRun={onRun} />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          <div className="agent-table-mobile">
            <div className="agent-mobile-sort" role="group" aria-label="Sort agents">
              <SortButton label="Name" sortKey="name" sort={sort} onSort={toggleSort} />
              <SortButton label="Last run" sortKey="lastRun" sort={sort} onSort={toggleSort} />
            </div>
            {visibleAgents.map((agent) => {
              const id = agent.agent_id || agent.id
              const active = agent.is_active !== false
              return (
                <article
                  className="agent-mobile-row"
                  key={id}
                  role="group"
                  aria-label={`Agent ${agent.name}`}
                  onClick={(event) => openDetailsForRow(event, agent, onDetails)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <button
                      type="button"
                      className="agent-name min-w-0 text-left"
                      onClick={() => onDetails?.(agent)}
                      aria-label={`View details for ${agent.name}`}
                    >
                      {agent.name}
                      {agent.description && (
                        <span className="agent-description" title={agent.description}>
                          {agent.description}
                        </span>
                      )}
                    </button>
                    {showStatus && <Status active={active} />}
                  </div>
                  <dl className="agent-mobile-meta">
                    <div><dt>Type</dt><dd>{getAgentTypeLabel(agent)}</dd></div>
                    <div><dt>Model</dt><dd>{getModel(agent)}</dd></div>
                    <div><dt>Last run</dt><dd><LastRun agent={agent} lastRuns={lastRuns} /></dd></div>
                  </dl>
                  <div className="table-actions">
                    <RunButton agent={agent} onRun={onRun} />
                  </div>
                </article>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export const AgentTableSkeleton = ({ rows = 4 }) => (
  <div className="agent-table-section" aria-label="Loading agents" role="status" aria-busy="true">
    <div className="table-toolbar">
      <span className="skeleton table-search-skeleton" />
    </div>
    <div className="agent-table-wrap">
      <div className="agent-table-skeleton-header">
        {['Name', 'Status', 'Type', 'Model', 'Last run'].map((label) => (
          <span key={label} className="skeleton h-3 w-16" />
        ))}
      </div>
      {Array.from({ length: rows }, (_, index) => (
        <div className="agent-table-skeleton-row" key={index}>
          <span className="skeleton h-3 w-40" />
          <span className="skeleton h-3 w-14" />
          <span className="skeleton h-3 w-20" />
          <span className="skeleton h-3 w-28" />
          <span className="skeleton h-3 w-16" />
          <span className="skeleton h-7 w-16" />
        </div>
      ))}
      <span className="sr-only">Loading agents</span>
    </div>
  </div>
)

export default AgentTable
