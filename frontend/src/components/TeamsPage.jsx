import { useCallback, useEffect, useRef, useState } from 'react'
import { agentService, isCoordinatorAgent, runService, teamService } from '../services/api'
import Button from './Button'
import RefreshButton from './RefreshButton'

const emptyForm = {
  name: '',
  description: '',
  hostAgentId: '',
  memberAgentIds: [],
  mode: 'coordinate',
  config: '{}',
  isPublic: false,
  isActive: true,
}

const idOf = (record) => String(record.agent_id || record.id)

const formFromTeam = (team) => ({
  ...emptyForm,
  name: team.name || '',
  description: team.description || '',
  hostAgentId: String(team.host_agent_id || ''),
  memberAgentIds: (team.members || []).map((member) => String(member.agent_id)),
  mode: team.mode || 'coordinate',
  config: JSON.stringify(team.config || {}, null, 2),
  isPublic: team.is_public === true,
  isActive: team.is_active !== false,
})

const TeamsPage = ({ onToast }) => {
  const [teams, setTeams] = useState([])
  const [agents, setAgents] = useState([])
  const [hostAgents, setHostAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editorTeam, setEditorTeam] = useState(null)
  const [editorOpen, setEditorOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [runTarget, setRunTarget] = useState(null)
  const [runPrompt, setRunPrompt] = useState('')
  const [runId, setRunId] = useState('')
  const [runState, setRunState] = useState('idle')
  const [runOutput, setRunOutput] = useState('')
  const [runError, setRunError] = useState('')
  const streamRef = useRef(null)
  const editorDialogRef = useRef(null)
  const deleteDialogRef = useRef(null)
  const runDialogRef = useRef(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [teamList, agentList, hostList] = await Promise.all([
        teamService.list(),
        agentService.getAgents(),
        agentService.getHostAgents(),
      ])
      setTeams(Array.isArray(teamList) ? teamList : [])
      setAgents(Array.isArray(agentList) ? agentList.filter((agent) => !isCoordinatorAgent(agent)) : [])
      setHostAgents(Array.isArray(hostList) ? hostList : [])
      return true
    } catch (requestError) {
      setError(requestError.message || 'Could not load teams.')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => () => streamRef.current?.(), [])

  const openCreate = useCallback(() => {
    setEditorTeam(null)
    setForm(emptyForm)
    setFormError('')
    setEditorOpen(true)
  }, [])

  const openEdit = useCallback((team) => {
    setEditorTeam(team)
    setForm(formFromTeam(team))
    setFormError('')
    setEditorOpen(true)
  }, [])

  const closeEditor = useCallback(() => {
    if (!saving) setEditorOpen(false)
  }, [saving])

  const closeDelete = useCallback(() => {
    if (!deleting) setDeleteTarget(null)
  }, [deleting])

  const updateForm = (key) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value
    setForm((current) => ({ ...current, [key]: value }))
  }

  const toggleMember = (agentId) => {
    setForm((current) => ({
      ...current,
      memberAgentIds: current.memberAgentIds.includes(agentId)
        ? current.memberAgentIds.filter((id) => id !== agentId)
        : [...current.memberAgentIds, agentId],
    }))
  }

  const saveTeam = async (event) => {
    event.preventDefault()
    const name = form.name.trim()
    const hostAgentId = Number(form.hostAgentId)
    const memberAgentIds = [...new Set(form.memberAgentIds.map(Number))]
    if (!name || !Number.isInteger(hostAgentId) || hostAgentId < 1 || memberAgentIds.length === 0) {
      setFormError('Enter a team name, choose a coordinator, and select at least one member.')
      return
    }

    let config
    if (!editorTeam) {
      try {
        config = JSON.parse(form.config)
      } catch {
        setFormError('Team configuration must be valid JSON.')
        return
      }
      if (!config || typeof config !== 'object' || Array.isArray(config)) {
        setFormError('Team configuration must be a JSON object.')
        return
      }
    }

    setSaving(true)
    setFormError('')
    try {
      if (editorTeam) {
        await teamService.update(editorTeam.team_id, {
          name,
          description: form.description.trim(),
          hostAgentId,
          memberAgentIds,
          mode: form.mode,
          is_active: form.isActive,
        })
      } else {
        await teamService.create({
          name,
          description: form.description.trim() || null,
          hostAgentId,
          memberAgentIds,
          mode: form.mode,
          config,
          is_public: form.isPublic,
        })
      }
      setEditorOpen(false)
      const refreshed = await refresh()
      onToast?.(
        refreshed
          ? (editorTeam ? 'Team updated' : 'Team created')
          : 'Team saved, but the list could not be refreshed',
        refreshed ? 'success' : 'danger'
      )
    } catch (requestError) {
      setFormError(requestError.message || `Could not ${editorTeam ? 'update' : 'create'} team.`)
    } finally {
      setSaving(false)
    }
  }

  const deleteTeam = async () => {
    if (!deleteTarget?.team_id) return
    setDeleting(true)
    setDeleteError('')
    try {
      await teamService.delete(deleteTarget.team_id)
      setDeleteTarget(null)
      const refreshed = await refresh()
      onToast?.(
        refreshed ? 'Team deleted' : 'Team deleted, but the list could not be refreshed',
        refreshed ? 'success' : 'danger'
      )
    } catch (requestError) {
      setDeleteError(requestError.message || 'Could not delete team.')
    } finally {
      setDeleting(false)
    }
  }

  const startRun = async (event) => {
    event.preventDefault()
    const prompt = runPrompt.trim()
    if (!prompt || !runTarget) return
    setRunState('starting')
    setRunOutput('')
    setRunError('')
    setRunId('')
    try {
      const record = await teamService.run(runTarget.team_id, prompt)
      setRunId(record.run_id)
      setRunState('running')
      streamRef.current?.()
      streamRef.current = runService.stream(record.run_id, {
        onEvent: (eventData) => {
          if (eventData.type === 'token') {
            setRunOutput((current) => current + (eventData.text || ''))
          }
        },
        onDone: (eventData) => {
          setRunOutput(eventData.output || '')
          setRunState('completed')
          onToast?.('Team run completed')
        },
        onError: (streamError) => {
          setRunError(streamError.message || 'The run failed.')
          setRunState('error')
          onToast?.('Team run failed', 'danger')
        },
      })
    } catch (requestError) {
      setRunError(requestError.message || 'Could not start the team run.')
      setRunState('error')
    }
  }

  const closeRun = useCallback(() => {
    if (runState === 'running' || runState === 'starting') return
    setRunTarget(null)
    setRunPrompt('')
    setRunState('idle')
    setRunOutput('')
    setRunError('')
    setRunId('')
  }, [runState])

  useEffect(() => {
    let dialog
    let dismiss
    let canDismiss = true
    if (editorOpen) {
      dialog = editorDialogRef.current
      dismiss = closeEditor
      canDismiss = !saving
    } else if (deleteTarget) {
      dialog = deleteDialogRef.current
      dismiss = closeDelete
      canDismiss = !deleting
    } else if (runTarget) {
      dialog = runDialogRef.current
      dismiss = closeRun
      canDismiss = runState !== 'running' && runState !== 'starting'
    }
    if (!dialog) return undefined

    const previouslyFocused = document.activeElement
    const focusableSelector = 'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)'
    const focusable = () => [...dialog.querySelectorAll(focusableSelector)]
    const initial = dialog.querySelector('[data-dialog-initial-focus]') || focusable()[0]
    initial?.focus()

    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && canDismiss) {
        event.preventDefault()
        dismiss()
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
  }, [closeDelete, closeEditor, closeRun, deleteTarget, deleting, editorOpen, runState, runTarget, saving])

  return (
    <div className="page-stack">
      <div className="flex flex-wrap justify-end gap-2">
        <RefreshButton loading={loading} onClick={() => void refresh()} />
        <Button onClick={openCreate}>Create team</Button>
      </div>

      {error && (
        <div className="feedback-error" role="alert">
          <p>{error}</p>
          <Button variant="secondary" size="sm" onClick={() => void refresh()} disabled={loading}>Retry</Button>
        </div>
      )}

      {loading && teams.length === 0 ? (
        <div className="surface table-empty" role="status">Loading teams…</div>
      ) : teams.length === 0 && !error ? (
        <section className="empty-state">
          <h2 className="section-title">No saved teams</h2>
          <p className="body-copy">Save a coordinator and its member agents together to reuse the same team.</p>
          <Button onClick={openCreate}>Create team</Button>
        </section>
      ) : teams.length > 0 ? (
        <div className="surface overflow-x-auto">
          <table className="agent-table min-w-full">
            <thead>
              <tr>
                <th scope="col">Team</th>
                <th scope="col">Coordinator</th>
                <th scope="col">Members</th>
                <th scope="col">Mode</th>
                <th scope="col">Status</th>
                <th scope="col">Visibility</th>
                <th scope="col"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {teams.map((team) => {
                const host = hostAgents.find((agent) => idOf(agent) === String(team.host_agent_id))
                const memberNames = (team.members || []).map((member) => member.name).filter(Boolean)
                return (
                  <tr key={team.team_id}>
                    <td>
                      <span className="agent-name">{team.name}</span>
                      {team.description && <p className="agent-description">{team.description}</p>}
                    </td>
                    <td>{host?.name || `Coordinator #${team.host_agent_id}`}</td>
                    <td title={memberNames.join(', ')}>{memberNames.length} agent{memberNames.length === 1 ? '' : 's'}</td>
                    <td className="capitalize">{team.mode}</td>
                    <td>{team.is_active === false ? 'Inactive' : 'Active'}</td>
                    <td>{team.is_public ? 'Public' : 'Private'}</td>
                    <td>
                      <div className="table-actions">
                        <Button variant="ghost" size="sm" disabled={team.is_active === false} onClick={() => {
                          setRunTarget(team)
                          setRunPrompt('')
                          setRunState('idle')
                          setRunOutput('')
                          setRunError('')
                          setRunId('')
                        }}>Run</Button>
                        <Button variant="ghost" size="sm" onClick={() => openEdit(team)}>Edit</Button>
                        <Button variant="ghost" size="sm" onClick={() => {
                          setDeleteError('')
                          setDeleteTarget(team)
                        }}>Delete</Button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {editorOpen && (
        <div className="modal-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeEditor()
        }}>
          <section ref={editorDialogRef} className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="team-editor-title">
            <div className="border-b border-border px-5 py-4">
              <h2 id="team-editor-title" className="section-title">{editorTeam ? 'Edit team' : 'Create team'}</h2>
            </div>
            <form onSubmit={saveTeam} className="grid gap-4 p-5 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label htmlFor="team-name" className="field-label">Name</label>
                <input id="team-name" data-dialog-initial-focus className="input-primary" value={form.name} onChange={updateForm('name')} maxLength={255} required disabled={saving} />
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="team-description" className="field-label">Description</label>
                <textarea id="team-description" className="input-primary min-h-20" rows={2} value={form.description} onChange={updateForm('description')} disabled={saving} />
              </div>
              <div>
                <label htmlFor="team-coordinator" className="field-label">Coordinator</label>
                <select id="team-coordinator" className="input-primary" value={form.hostAgentId} onChange={updateForm('hostAgentId')} required disabled={saving}>
                  <option value="">Select a coordinator</option>
                  {hostAgents.map((agent) => <option key={idOf(agent)} value={idOf(agent)}>{agent.name}</option>)}
                </select>
                {hostAgents.length === 0 && <p className="mt-1 text-xs text-muted">Create a coordinator from the Agents page first.</p>}
              </div>
              <div>
                <label htmlFor="team-mode" className="field-label">Mode</label>
                <select id="team-mode" className="input-primary" value={form.mode} onChange={updateForm('mode')} disabled={saving}>
                  <option value="coordinate">Coordinate</option>
                  <option value="route">Route</option>
                  <option value="collaborate">Collaborate</option>
                </select>
              </div>
              <fieldset className="sm:col-span-2">
                <legend className="field-label">Member agents (select at least one)</legend>
                {agents.length === 0 ? (
                  <p className="text-sm text-muted">Create an individual agent before saving a team.</p>
                ) : (
                  <div className="grid gap-2 sm:grid-cols-2">
                    {agents.map((agent) => {
                      const agentId = idOf(agent)
                      return (
                        <label key={agentId} className="flex items-center gap-2 rounded border border-border px-3 py-2 text-sm text-secondary">
                          <input type="checkbox" checked={form.memberAgentIds.includes(agentId)} onChange={() => toggleMember(agentId)} disabled={saving} />
                          <span>{agent.name}</span>
                          {agent.is_active === false && <span className="text-muted">(inactive)</span>}
                        </label>
                      )
                    })}
                  </div>
                )}
              </fieldset>
              {!editorTeam ? (
                <>
                  <div className="sm:col-span-2">
                    <label htmlFor="team-config" className="field-label">Team configuration (JSON)</label>
                    <textarea id="team-config" className="input-primary min-h-24 font-mono text-xs" rows={4} value={form.config} onChange={updateForm('config')} spellCheck={false} required disabled={saving} />
                    <p className="mt-1 text-xs text-muted">Optional team-level settings as a JSON object.</p>
                  </div>
                  <label className="flex items-center gap-2 text-sm text-secondary sm:col-span-2">
                    <input type="checkbox" checked={form.isPublic} onChange={updateForm('isPublic')} disabled={saving} />
                    Public to other users
                  </label>
                </>
              ) : (
                <div className="flex flex-wrap items-center gap-5 sm:col-span-2">
                  <span className="text-sm text-muted">Visibility: {editorTeam.is_public ? 'Public' : 'Private'}</span>
                  <label className="flex items-center gap-2 text-sm text-secondary">
                    <input type="checkbox" checked={form.isActive} onChange={updateForm('isActive')} disabled={saving} />
                    Active
                  </label>
                </div>
              )}
              {formError && <p className="feedback-error sm:col-span-2" role="alert">{formError}</p>}
              <div className="flex justify-end gap-2 border-t border-border pt-4 sm:col-span-2">
                <Button variant="secondary" onClick={closeEditor} disabled={saving}>Cancel</Button>
                <Button type="submit" loading={saving} loadingText={editorTeam ? 'Saving…' : 'Creating…'}>{editorTeam ? 'Save changes' : 'Create team'}</Button>
              </div>
            </form>
          </section>
        </div>
      )}

      {deleteTarget && (
        <div className="modal-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeDelete()
        }}>
          <section ref={deleteDialogRef} className="modal-panel confirm-panel" role="alertdialog" aria-modal="true" aria-labelledby="delete-team-title">
            <h2 id="delete-team-title" className="section-title">Delete team?</h2>
            <p className="body-copy">“{deleteTarget.name}” will be removed. Its agents will not be deleted.</p>
            {deleteError && <p className="feedback-error" role="alert">{deleteError}</p>}
            <div className="dialog-actions">
              <Button variant="secondary" data-dialog-initial-focus onClick={closeDelete} disabled={deleting}>Cancel</Button>
              <Button variant="destructive" onClick={() => void deleteTeam()} loading={deleting} loadingText="Deleting…">Delete team</Button>
            </div>
          </section>
        </div>
      )}

      {runTarget && (
        <div className="modal-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeRun()
        }}>
          <section ref={runDialogRef} className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="team-run-title">
            <div className="border-b border-border px-5 py-4">
              <h2 id="team-run-title" className="section-title">Run {runTarget.name}</h2>
            </div>
            <div className="grid gap-4 p-5">
              {runState === 'idle' ? (
                <form onSubmit={startRun} className="grid gap-4">
                  <div>
                    <label htmlFor="team-run-prompt" className="field-label">Task prompt</label>
                    <textarea id="team-run-prompt" data-dialog-initial-focus className="input-primary min-h-28" rows={4} value={runPrompt} onChange={(event) => setRunPrompt(event.target.value)} required disabled={runState === 'starting'} />
                  </div>
                  {runError && <p className="feedback-error" role="alert">{runError}</p>}
                  <div className="flex justify-end gap-2">
                    <Button variant="secondary" onClick={closeRun}>Cancel</Button>
                    <Button type="submit" loading={runState === 'starting'} loadingText="Starting…">Start run</Button>
                  </div>
                </form>
              ) : (
                <>
                  <div className="flex items-center justify-between gap-3 text-sm text-secondary">
                    <span role="status">{{
                      starting: 'Starting run…',
                      running: 'Run in progress',
                      completed: 'Run completed',
                      error: 'Run failed',
                    }[runState]}</span>
                    {runId && <span className="font-mono text-xs text-muted">{runId}</span>}
                  </div>
                  {runError && <p className="feedback-error" role="alert">{runError}</p>}
                  <div className="surface max-h-80 overflow-auto whitespace-pre-wrap p-4 text-sm leading-6" role="log" aria-label="Team run output">
                    {runOutput || (runState === 'starting' ? 'Submitting the team run…' : runState === 'running' ? 'Waiting for output…' : 'No output returned.')}
                  </div>
                  {runState !== 'running' && runState !== 'starting' && (
                    <div className="flex justify-end gap-2">
                      {(runState === 'completed' || runState === 'error') && (
                        <Button variant="secondary" onClick={() => {
                          setRunState('idle')
                          setRunError('')
                          setRunOutput('')
                          setRunId('')
                        }}>Run again</Button>
                      )}
                      <Button variant="secondary" onClick={closeRun}>Close</Button>
                    </div>
                  )}
                  {(runState === 'running' || runState === 'starting') && <p className="text-xs text-muted">Keep this window open to follow the live output.</p>}
                </>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default TeamsPage
