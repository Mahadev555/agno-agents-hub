import { useCallback, useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'
import { getAgentTypeLabel, isCoordinatorAgent } from '../services/agentTypes'
import { agentService } from '../services/api'
import { useAgentCatalog } from '../hooks/useAgentCatalog'
import AgentCreateModal from './AgentCreateModal'
import AgentTable, { AgentTableSkeleton } from './AgentTable'
import Button from './Button'
import RefreshButton from './RefreshButton'

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
  const {
    agents,
    hostAgents,
    allAgents,
    lastRuns,
    runHistoryError,
    loading,
    error,
    refresh,
  } = useAgentCatalog(refreshKey)
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [editingAgent, setEditingAgent] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const detailsRef = useRef(null)
  const deleteDialogRef = useRef(null)

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

  useEffect(() => {
    if (!deleteTarget) return undefined
    const dialog = deleteDialogRef.current
    const previouslyFocused = document.activeElement
    dialog?.querySelector('button')?.focus()
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && !deleting) {
        setDeleteTarget(null)
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
  }, [deleteTarget, deleting])

  const isCoordinator = selectedAgent && isCoordinatorAgent(selectedAgent)
  const selectedId = selectedAgent && (selectedAgent.agent_id || selectedAgent.id)

  const closeDetails = useCallback(() => setSelectedAgent(null), [])
  const handleRefresh = async () => {
    const result = await refresh()
    if (!result.success) {
      onToast?.('Could not refresh agents', 'danger')
      return
    }
    onToast?.(
      result.historyLoaded ? 'Agents refreshed' : 'Agents refreshed without run details',
      result.historyLoaded ? 'success' : 'danger'
    )
  }
  const handleAgentSaved = useCallback(async () => {
    const result = await refresh()
    if (!result.success) {
      onToast?.('Agent was saved, but the list could not be refreshed', 'danger')
      return
    }
    onToast?.('Agent updated')
  }, [onToast, refresh])

  const handleDelete = async () => {
    const agentId = deleteTarget?.agent_id || deleteTarget?.id
    if (!agentId) {
      setDeleteError('The selected agent has no ID and cannot be deleted.')
      return
    }
    setDeleting(true)
    setDeleteError('')
    try {
      await agentService.deleteAgent(agentId)
      setDeleteTarget(null)
      const result = await refresh()
      onToast?.(
        result.success ? 'Agent deleted' : 'Agent deleted, but the list could not be refreshed',
        result.success ? 'success' : 'danger'
      )
    } catch (deleteRequestError) {
      setDeleteError(deleteRequestError.message || 'Could not delete agent.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="page-stack">
      <div className="flex justify-end">
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
            <div className="flex items-center justify-between gap-4 border-b border-border px-5 py-4">
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
                  <p className="max-h-40 overflow-auto whitespace-pre-wrap text-sm leading-5 text-secondary">
                    {selectedAgent.config.instructions}
                  </p>
                </div>
              )}
              <dl className="agent-details-grid">
                <div><dt>Type</dt><dd>{getAgentTypeLabel(selectedAgent)}</dd></div>
                <div><dt>Status</dt><dd>{selectedAgent.is_active === false ? 'Inactive' : 'Active'}</dd></div>
                <div><dt>Visibility</dt><dd>{selectedAgent.is_public ? 'Public' : 'Private'}</dd></div>
                <div><dt>Model</dt><dd>{getModel(selectedAgent)}</dd></div>
                <div><dt>Agent ID</dt><dd className="font-mono">{selectedId}</dd></div>
                {isCoordinator && selectedAgent.config?.mode && (
                  <div><dt>Coordination mode</dt><dd>{selectedAgent.config.mode}</dd></div>
                )}
                {selectedAgent.mcp_config?.url && (
                  <div className="sm:col-span-2">
                    <dt>MCP server</dt>
                    <dd className="break-all">{selectedAgent.mcp_config.url}</dd>
                    <dd>{selectedAgent.mcp_config.transport} · {selectedAgent.mcp_config.timeout_seconds}s timeout</dd>
                  </div>
                )}
              </dl>
            </div>
            <div className="flex flex-wrap justify-end gap-2 border-t border-border px-5 py-4">
              <Button variant="secondary" onClick={closeDetails}>Close</Button>
              <Button
                variant="secondary"
                onClick={() => {
                  setEditingAgent(selectedAgent)
                  closeDetails()
                }}
              >
                Edit
              </Button>
              <Button
                variant="destructive"
                onClick={() => {
                  setDeleteError('')
                  setDeleteTarget(selectedAgent)
                  closeDetails()
                }}
              >
                Delete
              </Button>
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
      <AgentCreateModal
        open={Boolean(editingAgent)}
        agent={editingAgent}
        onClose={() => setEditingAgent(null)}
        onSaved={() => {
          setEditingAgent(null)
          void handleAgentSaved()
        }}
      />
      {deleteTarget && (
        <div
          className="modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !deleting) setDeleteTarget(null)
          }}
        >
          <section
            ref={deleteDialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-agent-title"
            className="modal-panel"
          >
            <div className="grid gap-4 p-5">
              <div>
                <h2 id="delete-agent-title" className="section-title">Delete agent?</h2>
                <p className="mt-2 body-copy">
                  “{deleteTarget.name}” will be permanently removed. Existing run history may remain.
                </p>
              </div>
              {deleteError && <p className="feedback-error" role="alert">{deleteError}</p>}
              <div className="flex justify-end gap-2">
                <Button variant="secondary" onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</Button>
                <Button variant="destructive" onClick={() => void handleDelete()} disabled={deleting} loading={deleting} loadingText="Deleting…">Delete agent</Button>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default AgentComponent
