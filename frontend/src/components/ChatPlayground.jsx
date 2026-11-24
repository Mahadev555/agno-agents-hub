import { useCallback, useEffect, useRef, useState } from 'react'
import { Copy, Loader2, Send, Trash2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { agentService, isCoordinatorAgent, runService } from '../services/api'
import Button from './Button'
import Select from './Select'

const promptExamples = [
  'Summarize the key points in this document.',
  'Review this code for bugs and edge cases.',
  'Draft a step-by-step plan for this task.',
]

const getModel = (agent) =>
  agent.config?.model_config?.id ||
  agent.config?.model?.id ||
  agent.config?.model_id ||
  '—'

const ChatPlayground = ({ initialAgentId, initialHostAgentId, onToast }) => {
  const [agents, setAgents] = useState([])
  const [hostAgents, setHostAgents] = useState([])
  const [executionMode, setExecutionMode] = useState('single')
  const [selectedAgent, setSelectedAgent] = useState('')
  const [selectedHostAgent, setSelectedHostAgent] = useState('')
  const [selectedMembers, setSelectedMembers] = useState([])
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingAgents, setLoadingAgents] = useState(true)
  const [elapsed, setElapsed] = useState(0)
  const [toolActivity, setToolActivity] = useState(null)
  const [error, setError] = useState(null)
  const [agentLoadError, setAgentLoadError] = useState(null)
  const [confirmClear, setConfirmClear] = useState(false)
  const transcriptRef = useRef(null)
  const promptRef = useRef(null)
  const clearTriggerRef = useRef(null)
  const clearDialogRef = useRef(null)
  const shouldAutoScrollRef = useRef(true)
  const streamingIdRef = useRef(null)
  const cancelStreamRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    const transcript = transcriptRef.current
    if (transcript) transcript.scrollTop = transcript.scrollHeight
  }, [])

  // Close any open stream if the user navigates away mid-run.
  useEffect(() => () => cancelStreamRef.current?.(), [])

  useEffect(() => {
    if (shouldAutoScrollRef.current) scrollToBottom()
  }, [messages, scrollToBottom])

  useEffect(() => {
    if (!confirmClear) return undefined

    const dialog = clearDialogRef.current
    const cancelButton = dialog?.querySelector('[data-dialog-cancel]')
    cancelButton?.focus()

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        setConfirmClear(false)
        return
      }
      if (event.key !== 'Tab' || !dialog) return
      const focusable = [...dialog.querySelectorAll('button:not(:disabled)')]
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      if (clearTriggerRef.current && !clearTriggerRef.current.disabled) {
        clearTriggerRef.current.focus()
      } else {
        promptRef.current?.focus()
      }
    }
  }, [confirmClear])

  // Team runs legitimately take 20-60s+, so show progress rather than an
  // indefinite spinner.
  useEffect(() => {
    if (!loading) {
      setElapsed(0)
      return
    }
    const startedAt = Date.now()
    const timer = setInterval(
      () => setElapsed(Math.floor((Date.now() - startedAt) / 1000)),
      1000
    )
    return () => clearInterval(timer)
  }, [loading])

  const fetchAgents = useCallback(async () => {
    try {
      const data = await agentService.getAgents()
      const agentList = Array.isArray(data) ? data.filter(agent => !isCoordinatorAgent(agent)) : []
      setAgents(agentList)
      if (agentList.length > 0) {
        const firstAgentId = String(agentList[0].agent_id || agentList[0].id)
        setSelectedAgent((current) => current || firstAgentId)
      }
    } catch (err) {
      setAgentLoadError((current) => [current, `Could not load agents: ${err.message}`].filter(Boolean).join(' '))
    }
  }, [])

  const fetchHostAgents = useCallback(async () => {
    try {
      const data = await agentService.getHostAgents()
      const hostAgentList = Array.isArray(data) ? data : []
      setHostAgents(hostAgentList)
      if (hostAgentList.length > 0) {
        const firstHostAgentId = String(hostAgentList[0].agent_id || hostAgentList[0].id)
        setSelectedHostAgent((current) => current || firstHostAgentId)
      }
    } catch (err) {
      setAgentLoadError((current) => [
        current,
        `Could not load coordinators: ${err.message}`,
      ].filter(Boolean).join(' '))
    }
  }, [])

  const loadCatalog = useCallback(async () => {
    setLoadingAgents(true)
    setAgentLoadError(null)
    await Promise.all([fetchAgents(), fetchHostAgents()])
    setLoadingAgents(false)
  }, [fetchAgents, fetchHostAgents])

  useEffect(() => {
    void loadCatalog()
  }, [loadCatalog])

  useEffect(() => {
    if (initialAgentId) {
      setSelectedAgent(String(initialAgentId))
      setExecutionMode('single')
    }
    if (initialHostAgentId) {
      setSelectedHostAgent(String(initialHostAgentId))
      setExecutionMode('team')
    }
  }, [initialAgentId, initialHostAgentId])

  const handleTranscriptScroll = () => {
    const transcript = transcriptRef.current
    if (!transcript) return
    shouldAutoScrollRef.current =
      transcript.scrollHeight - transcript.clientHeight - transcript.scrollTop < 48
  }

  const addMessage = (text, role, speaker) => {
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      text,
      role,
      speaker,
    }])
  }

  // Append streamed text to the in-progress agent message.
  const appendToStreaming = (text) => {
    setMessages(prev => prev.map(msg =>
      msg.id === streamingIdRef.current ? { ...msg, text: msg.text + text } : msg
    ))
  }

  const finalizeStreaming = (finalText) => {
    setMessages(prev => prev.map(msg =>
      msg.id === streamingIdRef.current
        ? { ...msg, text: finalText ?? msg.text, streaming: false }
        : msg
    ))
    streamingIdRef.current = null
  }

  /**
   * Start a run and render its output as it streams.
   *
   * Both modes share this path: one agent runs alone, several are coordinated
   * by the selected host agent.
   */
  const executeRun = async ({ agentIds, hostAgentId }) => {
    const prompt = input.trim()
    if (!prompt) return
    shouldAutoScrollRef.current = true
    addMessage(prompt, 'user', 'You')
    setInput('')
    setLoading(true)
    setError(null)
    setToolActivity(null)

    // Placeholder that streamed tokens flow into.
    const placeholderId = `stream-${Date.now()}`
    streamingIdRef.current = placeholderId
    const speaker = hostAgentId
      ? hostAgents.find((agent) => String(agent.agent_id || agent.id) === String(hostAgentId))?.name
      : agents.find((agent) => String(agent.agent_id || agent.id) === String(agentIds[0]))?.name
    setMessages(prev => [...prev, {
      id: placeholderId,
      text: '',
      role: 'agent',
      speaker: speaker || 'Agent',
      streaming: true,
    }])

    try {
      const run = await runService.start(prompt, { agentIds, hostAgentId })
      onToast?.('Run started')

      await new Promise((resolve) => {
        cancelStreamRef.current = runService.stream(run.run_id, {
          onEvent: (event) => {
            if (event.type === 'token') {
              appendToStreaming(event.text)
            } else if (event.type === 'tool_call') {
              setToolActivity(
                event.status === 'started' ? `Using ${event.name}...` : null
              )
            }
          },
          onDone: (event) => {
            // Prefer the server's assembled output over locally concatenated
            // tokens; they agree, but the server value is authoritative.
            finalizeStreaming(event.output)
            setToolActivity(null)
            onToast?.('Run finished')
            resolve()
          },
          onError: (err) => {
            finalizeStreaming()
            setMessages(prev => prev.filter(
              msg => !(msg.id === placeholderId && !msg.text)
            ))
            setError(err.message)
            addMessage('Error: ' + err.message, 'error', 'Run error')
            setToolActivity(null)
            onToast?.('Run failed', 'danger')
            resolve()
          },
        })
      })
    } catch (err) {
      // Failed before the stream existed (bad agent id, empty prompt, API down).
      finalizeStreaming()
      setMessages(prev => prev.filter(msg => msg.id !== placeholderId))
      setError(err.message)
      addMessage('Error: ' + err.message, 'error', 'Run error')
      onToast?.('Run failed', 'danger')
    } finally {
      cancelStreamRef.current = null
      setLoading(false)
    }
  }

  const handleExecuteSingle = async () => {
    if (!input.trim() || !selectedAgentOptions.some((option) => option.value === selectedAgent)) return
    await executeRun({ agentIds: [selectedAgent], hostAgentId: null })
  }

  const handleExecuteTeam = async () => {
    if (
      !input.trim() ||
      !selectedHostAgentOptions.some((option) => option.value === selectedHostAgent) ||
      selectedMembers.length === 0
    ) return
    await executeRun({ agentIds: selectedMembers, hostAgentId: selectedHostAgent })
  }

  const toggleMember = (agentId) => {
    setSelectedMembers(prev =>
      prev.includes(agentId)
        ? prev.filter(id => id !== agentId)
        : [...prev, agentId]
    )
  }

  const copyMessage = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      onToast?.('Response copied')
    } catch {
      const copyError = 'Could not copy the response. Check your browser clipboard permissions.'
      setError(copyError)
      onToast?.(copyError, 'danger')
    }
  }

  const handlePromptKeyDown = (event) => {
    if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
    event.preventDefault()
    if (executionMode === 'single') void handleExecuteSingle()
    else void handleExecuteTeam()
  }

  const clearConversation = () => {
    shouldAutoScrollRef.current = true
    setMessages([])
    setError(null)
    setConfirmClear(false)
  }

  const selectedAgentRecord = agents.find(
    (agent) => String(agent.agent_id || agent.id) === String(selectedAgent)
  )
  const selectedHostAgentRecord = hostAgents.find(
    (agent) => String(agent.agent_id || agent.id) === String(selectedHostAgent)
  )
  const selectedAgentOptions = agents.map((agent) => ({
    value: String(agent.agent_id || agent.id),
    label: agent.name,
    description: getModel(agent),
  }))
  const selectedHostAgentOptions = hostAgents.map((agent) => ({
    value: String(agent.agent_id || agent.id),
    label: agent.name,
    description: getModel(agent),
  }))

  return (
    <div className="chat-page">
      <div className="chat-mode-tabs" role="group" aria-label="Execution mode">
        {['single', 'team'].map((mode) => (
          <button
            key={mode}
            type="button"
            onClick={() => setExecutionMode(mode)}
            aria-pressed={executionMode === mode}
            className={`mode-button ${executionMode === mode ? 'mode-button-active' : ''}`}
          >
            {mode === 'single' ? 'Single agent' : 'Team'}
          </button>
        ))}
      </div>

      <div className="surface chat-config">
        {executionMode === 'single' ? (
          <Select
            id="selected-agent"
            label="Agent"
            value={selectedAgent}
            options={selectedAgentOptions}
            onChange={setSelectedAgent}
            placeholder={loadingAgents ? 'Loading agents…' : 'No agents available'}
            loading={loadingAgents}
          />
        ) : (
          <div className="chat-team-config">
            <Select
              id="selected-host-agent"
              label="Coordinator"
              value={selectedHostAgent}
              options={selectedHostAgentOptions}
              onChange={setSelectedHostAgent}
              placeholder={loadingAgents ? 'Loading coordinators…' : 'No coordinator agents available'}
              loading={loadingAgents}
            />
            <div>
              <span id="team-member-label" className="field-label">Agents</span>
              <div className="flex flex-wrap gap-2" role="group" aria-labelledby="team-member-label">
                {agents.map((agent) => {
                  const agentId = agent.agent_id || agent.id
                  const selected = selectedMembers.includes(agentId)
                  return (
                    <button
                      key={agentId}
                      type="button"
                      onClick={() => toggleMember(agentId)}
                      aria-pressed={selected}
                      className={`team-member ${selected ? 'team-member-active' : ''}`}
                    >
                      {agent.name}
                    </button>
                  )
                })}
                {agents.length === 0 && (
                  <p className="text-sm text-muted">Create an individual agent before configuring a team.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      <div
        ref={transcriptRef}
        className="surface chat-transcript"
        role="log"
        aria-label="Conversation"
        onScroll={handleTranscriptScroll}
      >
        {messages.length === 0 && (
          <div className="transcript-empty">
            <p>Choose an example or enter a task to start.</p>
            <div className="prompt-examples" aria-label="Example prompts">
              {promptExamples.map((example) => (
                <button
                  key={example}
                  type="button"
                  className="example-prompt"
                  onClick={() => {
                    setInput(example)
                    promptRef.current?.focus()
                  }}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((message) => {
          const speaker = message.speaker || (
            message.role === 'user'
              ? 'You'
              : message.role === 'error'
                ? 'Run error'
                : executionMode === 'team'
                  ? selectedHostAgentRecord?.name || 'Coordinator'
                  : selectedAgentRecord?.name || 'Agent'
          )
          return (
            <div
              key={message.id}
              className={`chat-message ${message.role === 'user' ? 'chat-message-user' : ''}`}
            >
              <div className={`message-bubble message-${message.role}`}>
                <div className="message-heading">
                  <span className="message-author">{speaker}</span>
                  {message.streaming && (
                    <span className="streaming-status" role="status" aria-live="polite">
                      <Loader2 className="refresh-spinner" size={14} aria-hidden="true" />
                      {toolActivity || (elapsed > 0 ? `Generating · ${elapsed}s` : 'Generating')}
                    </span>
                  )}
                </div>
                {message.role === 'agent' || message.role === 'system' ? (
                  <div className="chat-markdown">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p>{children}</p>,
                        ul: ({ children }) => <ul>{children}</ul>,
                        ol: ({ children }) => <ol>{children}</ol>,
                        li: ({ children }) => <li>{children}</li>,
                        strong: ({ children }) => <strong>{children}</strong>,
                        em: ({ children }) => <em>{children}</em>,
                        pre: ({ children }) => <pre className="chat-code-block">{children}</pre>,
                        code: ({ children, className }) => (
                          <code className={className ? 'chat-code-block-content' : 'chat-code'}>
                            {children}
                          </code>
                        ),
                        a: ({ href, children }) => <a href={href}>{children}</a>,
                      }}
                    >
                      {message.text}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="message-text">{message.text}</p>
                )}
                {message.role === 'agent' && (
                  <button
                    type="button"
                    onClick={() => copyMessage(message.text)}
                    className="copy-button"
                    aria-label={`Copy response from ${speaker}`}
                    disabled={message.streaming || !message.text}
                  >
                    <Copy size={14} strokeWidth={1.5} aria-hidden="true" />
                    Copy
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <form
        className="surface chat-composer"
        onSubmit={(event) => {
          event.preventDefault()
          if (executionMode === 'single') void handleExecuteSingle()
          else void handleExecuteTeam()
        }}
      >
        {agentLoadError && (
          <div className="feedback-error" role="alert">
            <p>{agentLoadError}</p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void loadCatalog()}
              disabled={loadingAgents}
            >
              Retry
            </Button>
          </div>
        )}
        {error && (
          <div className="feedback-error" role="alert">
            {error}
          </div>
        )}
        <div className="chat-composer-row">
          <div className="prompt-field">
            <textarea
              ref={promptRef}
              rows={Math.min(5, Math.max(1, input.split('\n').length))}
              aria-label="Task prompt"
              aria-describedby="prompt-keyboard-hint"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handlePromptKeyDown}
              placeholder="Describe the task"
              className="input-primary prompt-textarea"
              disabled={loading}
            />
            <span id="prompt-keyboard-hint" className="prompt-hint">
              Enter to run · Shift+Enter for a new line
            </span>
          </div>
          <Button
            type="submit"
            disabled={
              loading ||
              !input.trim() ||
              (executionMode === 'single' &&
                !selectedAgentOptions.some((option) => option.value === selectedAgent)) ||
              (executionMode === 'team' &&
                (!selectedHostAgentOptions.some((option) => option.value === selectedHostAgent) ||
                  selectedMembers.length === 0))
            }
            className="button-primary"
            aria-busy={loading}
          >
            {loading
              ? <Loader2 className="refresh-spinner" size={16} aria-hidden="true" />
              : <Send size={16} strokeWidth={1.5} aria-hidden="true" />}
            {loading ? 'Running…' : 'Run'}
          </Button>
          <button
            ref={clearTriggerRef}
            type="button"
            onClick={() => setConfirmClear(true)}
            className="icon-button"
            aria-label="Clear conversation"
            title="Clear conversation"
            disabled={loading || messages.length === 0}
          >
            <Trash2 size={16} strokeWidth={1.5} aria-hidden="true" />
          </button>
        </div>
      </form>

      {confirmClear && (
        <div
          className="modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setConfirmClear(false)
          }}
        >
          <section
            ref={clearDialogRef}
            className="modal-panel confirm-panel"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="clear-conversation-title"
            aria-describedby="clear-conversation-description"
          >
            <h2 id="clear-conversation-title" className="section-title">Clear conversation?</h2>
            <p id="clear-conversation-description" className="body-copy">
              This removes the messages from this session.
            </p>
            <div className="dialog-actions">
              <Button variant="secondary" data-dialog-cancel onClick={() => setConfirmClear(false)}>
                Cancel
              </Button>
              <Button
                variant="secondary"
                className="button-destructive"
                onClick={clearConversation}
              >
                Clear conversation
              </Button>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default ChatPlayground
