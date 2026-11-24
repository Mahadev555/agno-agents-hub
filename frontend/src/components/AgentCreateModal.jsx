import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'
import { agentService } from '../services/api'
import Button from './Button'

const initialForm = {
  name: '',
  description: '',
  agentType: 'simple',
  role: '',
  instructions: '',
  modelId: 'gemini-2.5-flash-lite',
  modelType: 'google',
  maxTokens: '4096',
  markdown: true,
  showToolCalls: true,
}

const AgentCreateModal = ({ open, onClose, onCreated }) => {
  const [form, setForm] = useState(initialForm)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const dialogRef = useRef(null)
  const busyRef = useRef(busy)
  busyRef.current = busy

  useEffect(() => {
    if (!open) return undefined

    const dialog = dialogRef.current
    const previouslyFocused = document.activeElement
    dialog?.querySelector('input')?.focus()

    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && !busyRef.current) {
        onClose()
        return
      }
      if (event.key !== 'Tab' || !dialog) return

      const focusable = [...dialog.querySelectorAll(
        'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)'
      )]
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
  }, [open, onClose])

  if (!open) return null

  const update = (key) => (event) => {
    const value = event.target.type === 'checkbox'
      ? event.target.checked
      : event.target.value
    setForm((current) => ({ ...current, [key]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const name = form.name.trim()
    const modelId = form.modelId.trim()
    const maxTokens = Number(form.maxTokens)
    if (!name || !modelId || !Number.isInteger(maxTokens) || maxTokens < 100 || maxTokens > 32000) {
      setError('Enter a name, model ID, and token limit between 100 and 32,000.')
      return
    }

    setBusy(true)
    setError('')
    try {
      const config = {
        name,
        role: form.role.trim() || 'Assistant',
        description: form.description.trim(),
        instructions: form.instructions.trim(),
        tools: [],
        markdown: form.markdown,
        show_tool_calls: form.showToolCalls,
        model_config: {
          id: modelId,
          type: form.modelType,
          max_tokens: maxTokens,
        },
        additional_params: {},
      }

      await agentService.createAgent({
        name,
        description: form.description.trim() || undefined,
        agent_type: form.agentType,
        instructions: form.instructions.trim() || undefined,
        config,
        is_mcp: form.agentType === 'mcp',
      })
      setForm(initialForm)
      onClose()
      onCreated?.()
    } catch (requestError) {
      setError(requestError.message || 'Could not create agent.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy) onClose()
      }}
    >
      <section
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-agent-title"
        className="modal-panel"
      >
        <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div>
            <h2 id="create-agent-title" className="section-title">Create agent</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Close create agent dialog"
            disabled={busy}
          >
            <X size={16} strokeWidth={1.5} aria-hidden="true" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="grid gap-4 p-5 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label htmlFor="agent-name" className="field-label">Name</label>
            <input id="agent-name" value={form.name} onChange={update('name')} className="input-primary" required maxLength={255} disabled={busy} />
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="agent-description" className="field-label">Description</label>
            <textarea id="agent-description" value={form.description} onChange={update('description')} className="input-primary min-h-20" rows={2} disabled={busy} />
          </div>

          <div>
            <label htmlFor="agent-type" className="field-label">Type</label>
            <select id="agent-type" value={form.agentType} onChange={update('agentType')} className="input-primary" disabled={busy}>
              <option value="simple">Individual</option>
              <option value="mcp">MCP</option>
              <option value="host">Coordinator</option>
            </select>
          </div>
          <div>
            <label htmlFor="agent-role" className="field-label">Role</label>
            <input id="agent-role" value={form.role} onChange={update('role')} className="input-primary" disabled={busy} />
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="agent-instructions" className="field-label">Instructions</label>
            <textarea id="agent-instructions" value={form.instructions} onChange={update('instructions')} className="input-primary min-h-24" rows={3} disabled={busy} />
          </div>

          <div>
            <label htmlFor="agent-model" className="field-label">Model ID</label>
            <input id="agent-model" value={form.modelId} onChange={update('modelId')} className="input-primary" required disabled={busy} />
          </div>
          <div>
            <label htmlFor="agent-model-type" className="field-label">Provider</label>
            <select id="agent-model-type" value={form.modelType} onChange={update('modelType')} className="input-primary" disabled={busy}>
              <option value="google">Google</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </div>
          <div>
            <label htmlFor="agent-max-tokens" className="field-label">Max tokens</label>
            <input id="agent-max-tokens" type="number" min="100" max="32000" step="1" value={form.maxTokens} onChange={update('maxTokens')} className="input-primary" required disabled={busy} />
          </div>

          <div className="flex flex-wrap items-end gap-4 pb-2">
            <label className="flex items-center gap-2 text-sm text-secondary">
              <input type="checkbox" checked={form.markdown} onChange={update('markdown')} disabled={busy} />
              Markdown
            </label>
            <label className="flex items-center gap-2 text-sm text-secondary">
              <input type="checkbox" checked={form.showToolCalls} onChange={update('showToolCalls')} disabled={busy} />
              Show tool calls
            </label>
          </div>

          {error && (
            <div className="feedback-error sm:col-span-2" role="alert">{error}</div>
          )}

          <div className="flex justify-end gap-2 border-t border-border pt-4 sm:col-span-2">
            <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
            <Button type="submit" disabled={busy} loading={busy}>
              {busy ? 'Creating…' : 'Create agent'}
            </Button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default AgentCreateModal
