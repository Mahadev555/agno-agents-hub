import Button from './Button'

const getAgentType = (agent) => {
  if (agent.kind === 'host' || agent.agent_type === 'host') return 'Coordinator'
  if (agent.kind === 'mcp' || agent.agent_type === 'mcp' || agent.is_mcp) return 'MCP'
  return 'Individual'
}

const getModel = (agent) =>
  agent.config?.model_config?.id ||
  agent.config?.model?.id ||
  agent.config?.model_id ||
  '—'

const getLastRun = (agent, lastRuns) => {
  const timestamp = lastRuns[String(agent.agent_id || agent.id)] || agent.last_run_at
  if (!timestamp) return '—'
  const date = new Date(timestamp)
  return Number.isNaN(date.getTime())
    ? '—'
    : new Intl.DateTimeFormat(undefined, { dateStyle: 'short', timeStyle: 'short' }).format(date)
}

const Status = ({ active }) => (
  <span className="status-text">
    <span className={`status-dot ${active ? '' : 'status-dot-inactive'}`} aria-hidden="true" />
    {active ? 'Active' : 'Inactive'}
  </span>
)

const AgentTable = ({ agents, lastRuns = {}, onRun, onDetails }) => (
  <div className="agent-table-wrap">
    <table className="agent-table agent-table-desktop">
      <thead>
        <tr>
          <th scope="col">Name</th>
          <th scope="col">Status</th>
          <th scope="col">Type</th>
          <th scope="col">Model</th>
          <th scope="col">Last run</th>
          <th scope="col"><span className="sr-only">Actions</span></th>
        </tr>
      </thead>
      <tbody>
        {agents.map((agent) => {
          const id = agent.agent_id || agent.id
          const active = agent.is_active !== false
          const coordinator = getAgentType(agent) === 'Coordinator'
          return (
            <tr key={id}>
              <td>
                <button type="button" className="agent-name" onClick={() => onDetails?.(agent)}>
                  {agent.name}
                </button>
                {agent.description && (
                  <p className="agent-description">{agent.description}</p>
                )}
              </td>
              <td><Status active={active} /></td>
              <td>{getAgentType(agent)}</td>
              <td className="font-mono text-xs">{getModel(agent)}</td>
              <td>{getLastRun(agent, lastRuns)}</td>
              <td>
                <div className="table-actions">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="button-run"
                    disabled={!active}
                    onClick={() => onRun?.(id, coordinator)}
                  >
                    Run
                  </Button>
                  <button
                    type="button"
                    className="table-details"
                    onClick={() => onDetails?.(agent)}
                  >
                    Details
                  </button>
                </div>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>

    <div className="agent-table-mobile">
      {agents.map((agent) => {
        const id = agent.agent_id || agent.id
        const active = agent.is_active !== false
        const coordinator = getAgentType(agent) === 'Coordinator'
        return (
          <article className="agent-mobile-row" key={id}>
            <div className="flex items-start justify-between gap-3">
              <button type="button" className="agent-name min-w-0 text-left" onClick={() => onDetails?.(agent)}>
                {agent.name}
                {agent.description && <span className="agent-description">{agent.description}</span>}
              </button>
              <Status active={active} />
            </div>
            <dl className="agent-mobile-meta">
              <div><dt>Type</dt><dd>{getAgentType(agent)}</dd></div>
              <div><dt>Model</dt><dd>{getModel(agent)}</dd></div>
              <div><dt>Last run</dt><dd>{getLastRun(agent, lastRuns)}</dd></div>
            </dl>
            <div className="table-actions">
              <Button
                variant="ghost"
                size="sm"
                className="button-run"
                disabled={!active}
                onClick={() => onRun?.(id, coordinator)}
              >
                Run
              </Button>
              <button type="button" className="table-details" onClick={() => onDetails?.(agent)}>
                Details
              </button>
            </div>
          </article>
        )
      })}
    </div>
  </div>
)

export const AgentTableSkeleton = ({ rows = 4 }) => (
  <div className="agent-table-wrap" aria-label="Loading agents" role="status">
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
)

export default AgentTable
