import { useCallback, useEffect, useState } from 'react'
import {
  agentService,
  buildLatestRunByAgent,
  isCoordinatorAgent,
  runService,
} from '../services/api'
import Button from './Button'
import AgentTable, { AgentTableSkeleton } from './AgentTable'

const Dashboard = ({ onExecuteAgent, onViewAgent, onViewAgents, onCreateAgent, onToast }) => {
  const [agents, setAgents] = useState([])
  const [hostAgents, setHostAgents] = useState([])
  const [lastRuns, setLastRuns] = useState({})
  const [runHistoryError, setRunHistoryError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadAgents = useCallback(async (notify = false) => {
    setLoading(true)
    setError(null)
    try {
      const [agentsData, hostAgentsData] = await Promise.all([
        agentService.getAgents(),
        agentService.getHostAgents(),
      ])
      setAgents(Array.isArray(agentsData) ? agentsData.filter(agent => !isCoordinatorAgent(agent)) : [])
      setHostAgents(Array.isArray(hostAgentsData) ? hostAgentsData : [])
      let historyLoaded = true
      try {
        const runs = await runService.list(200)
        setLastRuns(buildLatestRunByAgent(Array.isArray(runs) ? runs : []))
        setRunHistoryError(null)
      } catch (historyRequestError) {
        console.error('Failed to fetch recent runs:', historyRequestError)
        setLastRuns({})
        setRunHistoryError('Recent run data is unavailable.')
        historyLoaded = false
      }
      if (notify) {
        onToast?.(
          historyLoaded ? 'Overview refreshed' : 'Overview refreshed without run details',
          historyLoaded ? 'success' : 'danger'
        )
      }
    } catch (requestError) {
      console.error('Failed to fetch agents:', requestError)
      const message = requestError.message || 'Could not load agents.'
      setError(message)
      if (notify) onToast?.('Could not refresh overview', 'danger')
    } finally {
      setLoading(false)
    }
  }, [onToast])

  useEffect(() => {
    loadAgents()
  }, [loadAgents])

  const allAgents = [...agents, ...hostAgents]
  const stats = [
    { label: 'Total agents', value: allAgents.length },
    { label: 'Individual', value: agents.length },
    { label: 'Coordinators', value: hostAgents.length },
  ]

  const handleRefresh = () => loadAgents(true)

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
        <Button
          variant="secondary"
          size="sm"
          onClick={handleRefresh}
          disabled={loading}
          aria-label="Refresh overview"
        >
          Refresh
        </Button>
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
        <AgentTableSkeleton />
      ) : allAgents.length === 0 && !error ? (
        <section className="empty-state">
          <h2 className="section-title">No agents yet</h2>
          <p className="body-copy">Create an agent to start a run.</p>
          <Button onClick={onCreateAgent}>Create agent</Button>
        </section>
      ) : allAgents.length > 0 ? (
        <section className="page-stack" aria-labelledby="overview-agents-title">
          <div className="flex items-center justify-between gap-4">
            <h2 id="overview-agents-title" className="section-title">Agents</h2>
            <button type="button" className="table-details" onClick={onViewAgents}>View all</button>
          </div>
          <AgentTable
            agents={allAgents}
            lastRuns={lastRuns}
            onRun={onExecuteAgent}
            onDetails={onViewAgent}
          />
        </section>
      ) : null}
    </div>
  )
}

export default Dashboard
