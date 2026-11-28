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
  modelApiVersion: '',
  maxTokens: '4096',
  modelAdditionalParams: '{}',
  tools: '[]',
  additionalParams: '{}',
  coordinatorMode: 'coordinate',
  markdown: true,
  showToolCalls: true,
  isPublic: false,
  isActive: true,
  mcpUrl: '',
  mcpTransport: 'sse',
  mcpTimeoutSeconds: '300',
  mcpAdditionalParams: '{}',
}

const toJsonText = (value, fallback) => JSON.stringify(value ?? fallback, null, 2)

const formFromAgent = (agent) => {
  const config = agent.config || {}
  const model = config.model_config || config.model || {}
  const instructions = config.instructions
  return {
    ...initialForm,
    name: agent.name || '',
    description: agent.description || '',
    agentType: agent.agent_type || agent.kind || 'simple',
    role: config.role || '',
    instructions: Array.isArray(instructions) ? instructions.join('\n') : instructions || '',
    modelId: model.id || initialForm.modelId,
    modelType: model.type || initialForm.modelType,
    modelApiVersion: model.api_version || '',
    maxTokens: model.max_tokens == null ? '' : String(model.max_tokens),
    modelAdditionalParams: toJsonText(model.additional_params, {}),
    tools: toJsonText(config.tools, []),
    additionalParams: toJsonText(config.additional_params, {}),
    coordinatorMode: config.mode || agent.mode || 'coordinate',
    markdown: config.markdown !== false,
    showToolCalls: config.show_tool_calls !== false,
    isPublic: agent.is_public === true,
    isActive: agent.is_active !== false,
    mcpUrl: agent.mcp_config?.url || '',
    mcpTransport: agent.mcp_config?.transport || 'sse',
    mcpTimeoutSeconds: String(agent.mcp_config?.timeout_seconds || 300),
    mcpAdditionalParams: toJsonText(agent.mcp_config?.additional_params, {}),
  }
}

const AgentCreateModal = ({ open, onClose, onCreated, agent, onSaved }) => {
  const [form, setForm] = useState(initialForm)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const dialogRef = useRef(null)
  const busyRef = useRef(busy)
  busyRef.current = busy

  useEffect(() => {
    if (!open) return undefined

    setForm(agent ? formFromAgent(agent) : initialForm)
    setError('')
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
  }, [agent, open, onClose])

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
    const maxTokens = form.maxTokens.trim() ? Number(form.maxTokens) : undefined
    if (!name || !modelId || (maxTokens !== undefined &&
      (!Number.isInteger(maxTokens) || maxTokens < 1 || maxTokens > 200000))) {
      setError('Enter a name and model ID, and use a token limit from 1 to 200,000.')
      return
    }

    const parseObject = (value, label) => {
      let parsed
      try {
        parsed = JSON.parse(value)
      } catch {
        throw new Error(`${label} must be valid JSON.`)
      }
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error(`${label} must be a JSON object.`)
      }
      return parsed
    }

    let modelAdditionalParams
    let additionalParams
    let tools = []
    try {
      modelAdditionalParams = parseObject(form.modelAdditionalParams, 'Model additional parameters')
      additionalParams = parseObject(form.additionalParams, 'Agent additional parameters')
      if (form.agentType !== 'host') {
        try {
          tools = JSON.parse(form.tools)
        } catch {
          throw new Error('Tools must be valid JSON.')
        }
        if (!Array.isArray(tools) || tools.some((tool) => typeof tool !== 'string')) {
          throw new Error('Tools must be a JSON array of tool names.')
        }
      }
    } catch (validationError) {
      setError(validationError.message)
      return
    }

    const modelConfig = {
      id: modelId,
      type: form.modelType,
      ...(maxTokens === undefined ? {} : { max_tokens: maxTokens }),
      ...(form.modelApiVersion.trim() ? { api_version: form.modelApiVersion.trim() } : {}),
      additional_params: modelAdditionalParams,
    }
    const instructions = form.instructions.trim()
    const description = form.description.trim()
    const config = form.agentType === 'host'
      ? {
          name,
          description,
          mode: form.coordinatorMode,
          instructions,
          model_config: modelConfig,
          additional_params: additionalParams,
        }
      : {
          name,
          role: form.role.trim() || 'Assistant',
          description,
          instructions,
          tools,
          markdown: form.markdown,
          show_tool_calls: form.showToolCalls,
          model_config: modelConfig,
          additional_params: additionalParams,
        }

    let mcpConfig
    if (form.agentType === 'mcp') {
      const mcpUrl = form.mcpUrl.trim()
      const transport = form.mcpTransport
      const timeoutSeconds = Number(form.mcpTimeoutSeconds)
      if (!mcpUrl) {
        setError('Enter an MCP server URL.')
        return
      }

      try {
        const parsedUrl = new URL(mcpUrl)
        if (parsedUrl.protocol !== 'http:' && parsedUrl.protocol !== 'https:') {
          setError('MCP server URL must use HTTP or HTTPS.')
          return
        }
      } catch {
        setError('Enter a valid MCP server URL.')
        return
      }

      if (!Number.isInteger(timeoutSeconds) || timeoutSeconds < 1 || timeoutSeconds > 3600) {
        setError('MCP timeout must be a whole number from 1 to 3,600 seconds.')
        return
      }

      let mcpAdditionalParams
      try {
        mcpAdditionalParams = parseObject(form.mcpAdditionalParams, 'MCP additional parameters')
      } catch (validationError) {
        setError(validationError.message)
        return
      }

      mcpConfig = {
        url: mcpUrl,
        transport,
        timeout_seconds: timeoutSeconds,
        additional_params: mcpAdditionalParams,
      }
    }

    setBusy(true)
    setError('')
    try {
      if (agent) {
        const agentId = agent.agent_id || agent.id
        if (!agentId) throw new Error('The selected agent has no ID and cannot be updated.')
        const updateData = {
          name,
          description,
          config,
          is_active: form.isActive,
          is_public: form.isPublic,
        }
        if (mcpConfig) updateData.mcp_config = mcpConfig
        await agentService.updateAgent(agentId, updateData)
      } else {
        const agentData = {
          name,
          description: description || undefined,
          agent_type: form.agentType,
          instructions: instructions || undefined,
          config,
          is_mcp: form.agentType === 'mcp',
          is_public: form.isPublic,
        }
        if (mcpConfig) agentData.mcp_config = mcpConfig
        await agentService.createAgent(agentData)
      }

      setForm(initialForm)
      onClose()
      if (agent) onSaved?.()
      else onCreated?.()
    } catch (requestError) {
      setError(requestError.message || `Could not ${agent ? 'update' : 'create'} agent.`)
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
            <h2 id="create-agent-title" className="section-title">{agent ? 'Edit agent' : 'Create agent'}</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label={`Close ${agent ? 'edit' : 'create'} agent dialog`}
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
            <select id="agent-type" value={form.agentType} onChange={update('agentType')} className="input-primary" disabled={busy || Boolean(agent)}>
              <option value="simple">Individual</option>
              <option value="mcp">MCP</option>
              <option value="host">Coordinator</option>
            </select>
          </div>

          {form.agentType === 'host' && (
            <div>
              <label htmlFor="coordinator-mode" className="field-label">Coordination mode</label>
              <select id="coordinator-mode" value={form.coordinatorMode} onChange={update('coordinatorMode')} className="input-primary" disabled={busy}>
                <option value="coordinate">Coordinate</option>
                <option value="route">Route</option>
                <option value="collaborate">Collaborate</option>
              </select>
            </div>
          )}

          {form.agentType === 'mcp' && (
            <div className="grid gap-4 sm:col-span-2 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label htmlFor="mcp-server-url" className="field-label">MCP server URL</label>
                <input
                  id="mcp-server-url"
                  type="url"
                  value={form.mcpUrl}
                  onChange={update('mcpUrl')}
                  className="input-primary"
                  placeholder="https://mcp.example.com/sse"
                  required
                  disabled={busy}
                  aria-describedby="mcp-server-url-help"
                />
                <p id="mcp-server-url-help" className="mt-1 text-xs text-muted">
                  The server blocks private and loopback addresses unless explicitly allowlisted.
                </p>
              </div>
              <div>
                <label htmlFor="mcp-transport" className="field-label">Transport</label>
                <select id="mcp-transport" value={form.mcpTransport} onChange={update('mcpTransport')} className="input-primary" disabled={busy}>
                  <option value="sse">SSE</option>
                  <option value="stdio">STDIO</option>
                  <option value="streamable-http">Streamable HTTP</option>
                </select>
              </div>
              <div>
                <label htmlFor="mcp-timeout" className="field-label">Timeout (seconds)</label>
                <input
                  id="mcp-timeout"
                  type="number"
                  min="1"
                  max="3600"
                  step="1"
                  value={form.mcpTimeoutSeconds}
                  onChange={update('mcpTimeoutSeconds')}
                  className="input-primary"
                  required
                  disabled={busy}
                />
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="mcp-additional-params" className="field-label">Additional parameters (JSON)</label>
                <textarea
                  id="mcp-additional-params"
                  value={form.mcpAdditionalParams}
                  onChange={update('mcpAdditionalParams')}
                  className="input-primary min-h-24 font-mono text-xs"
                  rows={3}
                  spellCheck={false}
                  required
                  disabled={busy}
                  aria-describedby="mcp-additional-params-help"
                />
                <p id="mcp-additional-params-help" className="mt-1 text-xs text-muted">
                  Enter a JSON object, for example {'{}'}.
                </p>
              </div>
            </div>
          )}

          {form.agentType !== 'host' && <div>
            <label htmlFor="agent-role" className="field-label">Role</label>
            <input id="agent-role" value={form.role} onChange={update('role')} className="input-primary" disabled={busy} />
          </div>}

          <div className="sm:col-span-2">
            <label htmlFor="agent-instructions" className="field-label">Instructions</label>
            <textarea id="agent-instructions" value={form.instructions} onChange={update('instructions')} className="input-primary min-h-24" rows={3} disabled={busy} />
          </div>

          {form.agentType !== 'host' && (
            <div className="sm:col-span-2">
              <label htmlFor="agent-tools" className="field-label">Tools (JSON array)</label>
              <textarea
                id="agent-tools"
                value={form.tools}
                onChange={update('tools')}
                className="input-primary min-h-20 font-mono text-xs"
                rows={3}
                spellCheck={false}
                disabled={busy}
                aria-describedby="agent-tools-help"
              />
              <p id="agent-tools-help" className="mt-1 text-xs text-muted">
                Enter registered tool names as a JSON array, for example {'["duckduckgo"]'}.
              </p>
            </div>
          )}

          <div>
            <label htmlFor="agent-model" className="field-label">Model ID</label>
            <input id="agent-model" value={form.modelId} onChange={update('modelId')} className="input-primary" required disabled={busy} />
          </div>
          <div>
            <label htmlFor="agent-model-type" className="field-label">Provider</label>
            <select id="agent-model-type" value={form.modelType} onChange={update('modelType')} className="input-primary" disabled={busy}>
              <option value="google">Google</option>
              <option value="openai">OpenAI</option>
              <option value="azure">Azure OpenAI</option>
            </select>
          </div>
          <div>
            <label htmlFor="agent-max-tokens" className="field-label">Max tokens</label>
            <input id="agent-max-tokens" type="number" min="1" max="200000" step="1" value={form.maxTokens} onChange={update('maxTokens')} className="input-primary" disabled={busy} />
          </div>
          <div>
            <label htmlFor="agent-model-api-version" className="field-label">Model API version</label>
            <input id="agent-model-api-version" value={form.modelApiVersion} onChange={update('modelApiVersion')} className="input-primary" disabled={busy} />
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="model-additional-params" className="field-label">Model additional parameters (JSON)</label>
            <textarea id="model-additional-params" value={form.modelAdditionalParams} onChange={update('modelAdditionalParams')} className="input-primary min-h-20 font-mono text-xs" rows={3} spellCheck={false} required disabled={busy} />
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="agent-additional-params" className="field-label">Agent additional parameters (JSON)</label>
            <textarea id="agent-additional-params" value={form.additionalParams} onChange={update('additionalParams')} className="input-primary min-h-20 font-mono text-xs" rows={3} spellCheck={false} required disabled={busy} />
          </div>

          <div className="flex flex-wrap items-end gap-4 pb-2 sm:col-span-2">
            {form.agentType !== 'host' && (
              <>
                <label className="flex items-center gap-2 text-sm text-secondary">
                  <input type="checkbox" checked={form.markdown} onChange={update('markdown')} disabled={busy} />
                  Markdown
                </label>
                <label className="flex items-center gap-2 text-sm text-secondary">
                  <input type="checkbox" checked={form.showToolCalls} onChange={update('showToolCalls')} disabled={busy} />
                  Show tool calls
                </label>
              </>
            )}
            <label className="flex items-center gap-2 text-sm text-secondary">
              <input type="checkbox" checked={form.isPublic} onChange={update('isPublic')} disabled={busy} />
              Public to other users
            </label>
            {agent && (
              <label className="flex items-center gap-2 text-sm text-secondary">
                <input type="checkbox" checked={form.isActive} onChange={update('isActive')} disabled={busy} />
                Active
              </label>
            )}
          </div>

          {error && (
            <div className="feedback-error sm:col-span-2" role="alert">{error}</div>
          )}

          <div className="flex justify-end gap-2 border-t border-border pt-4 sm:col-span-2">
            <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
            <Button type="submit" disabled={busy} loading={busy} loadingText={agent ? 'Saving…' : 'Creating…'}>
              {busy ? (agent ? 'Saving…' : 'Creating…') : (agent ? 'Save changes' : 'Create agent')}
            </Button>
          </div>
        </form>
      </section>
    </div>
  )
}

export default AgentCreateModal
