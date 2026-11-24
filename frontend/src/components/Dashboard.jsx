import { AGENT_TYPE_LABELS, countAgentsByType } from '../services/agentTypes'
import { useAgentCatalog } from '../hooks/useAgentCatalog'
import Button from './Button'
import AgentTable, { AgentTableSkeleton } from './AgentTable'
import RefreshButton from './RefreshButton'

const Dashboard = ({ onExecuteAgent, onViewAgent, onViewAgents, onCreateAgent, onToast }) => {
  const {
    allAgents,
    lastRuns,
    runHistoryError,
    loading,
    error,
    refresh,
  } = useAgentCatalog()
  const agentCounts = countAgentsByType(allAgents)
  const stats = [
    { label: 'Total agents', value: allAgents.length },
    ...Object.entries(AGENT_TYPE_LABELS).map(([type, label]) => ({
      label,
      value: agentCounts[type],
    })),
  ]

  const handleRefresh = async () => {
    const result = await refresh()
    if (!result.success) {
      onToast?.('Could not refresh overview', 'danger')
      return
    }
    onToast?.(
      result.historyLoaded ? 'Overview refreshed' : 'Overview refreshed without run details',
      result.historyLoaded ? 'success' : 'danger'
    )
  }

  return (
    <div className="page-stack">
      <div className="overview-summary">
        <section className="metric-row" aria-label="Agent counts">
          {stats.map(({ label, value }) => (
            <div className="metric-item" key={label}>
              <span className="metric-value">
                {(loading || error) && allAgents.length === 0 ? '—' : value}
              </span>
              <span className="metric-label">{label}</span>
            </div>
          ))}
        </section>
        <RefreshButton loading={loading} onClick={handleRefresh} />
      </div>

      {error && (
        <div className="feedback-error" role="alert">
          <p>{error}</p>
          <Button variant="secondary" size="sm" onClick={handleRefresh} disabled={loading}>Retry</Button>
        </div>
      )}
      {runHistoryError && (
        <div className="feedback-warning" role="status">
          <p>{runHistoryError}</p>
          <Button variant="secondary" size="sm" onClick={handleRefresh} disabled={loading}>Retry</Button>
        </div>
      )}

      {loading && allAgents.length === 0 ? (
        <AgentTableSkeleton rows={5} />
      ) : allAgents.length === 0 && !error ? (
        <section className="empty-state">
          <h2 className="section-title">No agents yet</h2>
          <p className="body-copy">Create an agent to start a run.</p>
          <Button onClick={onCreateAgent}>Create agent</Button>
        </section>
      ) : allAgents.length > 0 ? (
        <section className="page-stack" aria-labelledby="overview-agents-title">
          <div className="flex items-center justify-between gap-4">
            <h2 id="overview-agents-title" className="section-title">
              {Object.keys(lastRuns).length > 0 ? 'Recently used agents' : 'Agents'}
            </h2>
            <button type="button" className="table-details" onClick={onViewAgents}>View all</button>
          </div>
          <AgentTable
            agents={allAgents}
            lastRuns={lastRuns}
            limit={5}
            initialSort="lastRun"
            initialDirection="desc"
            onRun={onExecuteAgent}
            onDetails={onViewAgent}
          />
        </section>
      ) : null}
    </div>
  )
}

export default Dashboard
