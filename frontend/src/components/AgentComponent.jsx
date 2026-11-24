import { useCallback, useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'
import {
  agentService,
  buildLatestRunByAgent,
  isCoordinatorAgent,
  runService,
} from '../services/api'
import AgentTable, { AgentTableSkeleton } from './AgentTable'
import Button from './Button'

const getModel = (agent) =>
  agent.config?.model_config?.id ||
  agent.config?.model?.id ||
  agent.config?.model_id ||
  '—'

const AgentComponent = ({
  selectedAgentId,
  onExecuteAgent,
  onSelectionHandled,
  onCreateAgent,
  onToast,
  refreshKey,
}) => {
  const [agents, setAgents] = useState([])
  const [hostAgents, setHostAgents] = useState([])
  const [lastRuns, setLastRuns] = useState({})
  const [runHistoryError, setRunHistoryError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedAgent, setSelectedAgent] = useState(null)
  const detailsRef = useRef(null)

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
          historyLoaded ? 'Agents refreshed' : 'Agents refreshed without run details',
          historyLoaded ? 'success' : 'danger'
        )
      }
    } catch (requestError) {
      console.error('Failed to fetch agents:', requestError)
      const message = requestError.message || 'Could not load agents.'
      setError(message)
      if (notify) onToast?.('Could not refresh agents', 'danger')
    } finally {
      setLoading(false)
    }
  }, [onToast])

  useEffect(() => {
    loadAgents()
  }, [loadAgents, refreshKey])

  useEffect(() => {
    if (!selectedAgentId || loading) return
    const agent = [...agents, ...hostAgents].find(
      item => String(item.agent_id || item.id) === String(selectedAgentId)
    )
    if (agent) setSelectedAgent(agent)
    onSelectionHandled?.()
  }, [selectedAgentId, agents, hostAgents, loading, onSelectionHandled])

  useEffect(() => {
    if (!selectedAgent) return undefined
    const dialog = detailsRef.current
    const previouslyFocused = document.activeElement
    dialog?.querySelector('button')?.focus()
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setSelectedAgent(null)
        return
      }
      if (event.key !== 'Tab' || !dialog) return
      const focusable = [...dialog.querySelectorAll('button:not(:disabled)')]
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
  }, [selectedAgent])

  const allAgents = [...agents, ...hostAgents]
  const isCoordinator = selectedAgent && isCoordinatorAgent(selectedAgent)
  const selectedId = selectedAgent && (selectedAgent.agent_id || selectedAgent.id)

  const closeDetails = () => setSelectedAgent(null)
  const handleRefresh = () => loadAgents(true)

  return (
    <div className="page-stack">
      <div className="flex justify-end">
        <Button variant="secondary" size="sm" onClick={handleRefresh} disabled={loading}>
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
        <AgentTable
          agents={allAgents}
          lastRuns={lastRuns}
          onRun={onExecuteAgent}
          onDetails={setSelectedAgent}
        />
      ) : null}

      {selectedAgent && (
        <div
          className="modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeDetails()
          }}
        >
          <section
            ref={detailsRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="agent-details-title"
            className="modal-panel"
          >
            <div className="flex items-center justify-between gap-4 border-b border-slate-200 px-5 py-4">
              <h2 id="agent-details-title" className="section-title">{selectedAgent.name}</h2>
              <button type="button" className="icon-button" onClick={closeDetails} aria-label="Close agent details">
                <X size={16} strokeWidth={1.5} aria-hidden="true" />
              </button>
            </div>
            <div className="grid gap-5 p-5">
              {selectedAgent.description && (
                <div>
                  <h3 className="field-label">Description</h3>
                  <p className="body-copy">{selectedAgent.description}</p>
                </div>
              )}
              {selectedAgent.config?.instructions && (
                <div>
                  <h3 className="field-label">Instructions</h3>
                  <p className="max-h-40 overflow-auto whitespace-pre-wrap text-sm leading-5 text-slate-600">
                    {selectedAgent.config.instructions}
                  </p>
                </div>
              )}
              <dl className="agent-details-grid">
                <div><dt>Type</dt><dd>{isCoordinator ? 'Coordinator' : selectedAgent.agent_type || 'Individual'}</dd></div>
                <div><dt>Status</dt><dd>{selectedAgent.is_active === false ? 'Inactive' : 'Active'}</dd></div>
                <div><dt>Model</dt><dd>{getModel(selectedAgent)}</dd></div>
                <div><dt>Agent ID</dt><dd className="font-mono">{selectedId}</dd></div>
              </dl>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-4">
              <Button variant="secondary" onClick={closeDetails}>Close</Button>
              <Button
                size="sm"
                disabled={selectedAgent.is_active === false}
                onClick={() => {
                  closeDetails()
                  onExecuteAgent?.(selectedId, isCoordinator)
                }}
              >
                Run
              </Button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default AgentComponent
