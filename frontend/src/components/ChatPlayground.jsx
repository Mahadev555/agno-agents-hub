import { useState, useEffect, useRef } from 'react'
import { Send, Trash2, Copy } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { agentService, isCoordinatorAgent, runService } from '../services/api'
import Button from './Button'

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
  const [elapsed, setElapsed] = useState(0)
  const [toolActivity, setToolActivity] = useState(null)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)
  const streamingIdRef = useRef(null)
  const cancelStreamRef = useRef(null)

  // Close any open stream if the user navigates away mid-run.
  useEffect(() => () => cancelStreamRef.current?.(), [])

  useEffect(() => {
    const initializeChat = async () => {
      await fetchAgents()
      await fetchHostAgents()
    }
    initializeChat()
    setMessages([])
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

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

  const fetchAgents = async () => {
    try {
      const data = await agentService.getAgents()
      const agentList = Array.isArray(data) ? data.filter(agent => !isCoordinatorAgent(agent)) : []
      setAgents(agentList)
      if (agentList.length > 0 && !initialAgentId) {
        setSelectedAgent(String(agentList[0].agent_id || agentList[0].id))
      }
    } catch (err) {
      console.error('Failed to fetch agents:', err)
      setError(err.message)
    }
  }

  const fetchHostAgents = async () => {
    try {
      const data = await agentService.getHostAgents()
      const hostAgentList = Array.isArray(data) ? data : []
      setHostAgents(hostAgentList)
      if (hostAgentList.length > 0 && !initialHostAgentId) {
        setSelectedHostAgent(String(hostAgentList[0].agent_id || hostAgentList[0].id))
      }
    } catch (err) {
      console.error('Failed to fetch host agents:', err)
      setError(err.message)
    }
  }

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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const addMessage = (text, role) => {
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      text,
      role,
      timestamp: new Date(),
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
    addMessage(input, 'user')
    const prompt = input
    setInput('')
    setLoading(true)
    setError(null)
    setToolActivity(null)

    // Placeholder that streamed tokens flow into.
    const placeholderId = `stream-${Date.now()}`
    streamingIdRef.current = placeholderId
    setMessages(prev => [...prev, {
      id: placeholderId,
      text: '',
      role: 'agent',
      streaming: true,
      timestamp: new Date(),
    }])

    try {
      const run = await runService.start(prompt, { agentIds, hostAgentId })

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
            onToast?.('Run completed')
            resolve()
          },
          onError: (err) => {
            finalizeStreaming()
            setMessages(prev => prev.filter(
              msg => !(msg.id === placeholderId && !msg.text)
            ))
            setError(err.message)
            addMessage('Error: ' + err.message, 'error')
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
      addMessage('Error: ' + err.message, 'error')
      onToast?.('Run failed', 'danger')
    } finally {
      cancelStreamRef.current = null
      setLoading(false)
    }
  }

  const handleExecuteSingle = async () => {
    if (!input.trim() || !selectedAgent) return
    await executeRun({ agentIds: [selectedAgent], hostAgentId: null })
  }

  const handleExecuteTeam = async () => {
    if (!input.trim() || !selectedHostAgent || selectedMembers.length === 0) return
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
    } catch (err) {
      console.error('Failed to copy agent response:', err)
      setError('Could not copy the response. Check your browser clipboard permissions.')
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-mode-tabs" role="group" aria-label="Execution mode">
        {['single', 'team'].map(mode => (
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
          <div>
            <label htmlFor="selected-agent" className="field-label">Agent</label>
            <select
              id="selected-agent"
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="input-primary"
            >
              {agents.length === 0 && <option value="">No agents available</option>}
              {agents.map(agent => (
                <option key={agent.agent_id || agent.id} value={agent.agent_id || agent.id}>
                  {agent.name}{agent.role ? ` (${agent.role})` : ''}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label htmlFor="selected-host-agent" className="field-label">Coordinator</label>
              <select
                id="selected-host-agent"
                value={selectedHostAgent}
                onChange={(e) => setSelectedHostAgent(e.target.value)}
                className="input-primary"
              >
                {hostAgents.length === 0 && <option value="">No coordinator agents available</option>}
                {hostAgents.map(agent => (
                  <option key={agent.agent_id || agent.id} value={agent.agent_id || agent.id}>
                    {agent.name}{agent.role ? ` (${agent.role})` : ''}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <span className="field-label">Agents</span>
              <div className="flex flex-wrap gap-2">
                {agents.map(agent => (
                  <button
                    key={agent.agent_id || agent.id}
                    type="button"
                    onClick={() => toggleMember(agent.agent_id || agent.id)}
                    aria-pressed={selectedMembers.includes(agent.agent_id || agent.id)}
                    className={`team-member ${selectedMembers.includes(agent.agent_id || agent.id) ? 'team-member-active' : ''}`}
                  >
                    {agent.name}
                  </button>
                ))}
                {agents.length === 0 && (
                  <p className="text-sm text-slate-500">Create an individual agent before configuring a team.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="surface chat-transcript" role="log" aria-label="Conversation">
          {messages.length === 0 && (
            <p className="transcript-empty">Enter a task to start a run.</p>
          )}
          {messages.map(msg => (
            <div
              key={msg.id}
              className={`chat-message ${msg.role === 'user' ? 'chat-message-user' : ''}`}
            >
              <div className={`message-bubble message-${msg.role}`}>
                {msg.role === 'agent' || msg.role === 'system' ? (
                  <div className="chat-markdown">
                    <ReactMarkdown
                      components={{
                        p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                        ul: ({children}) => <ul className="list-disc list-inside mb-2">{children}</ul>,
                        ol: ({children}) => <ol className="list-decimal list-inside mb-2">{children}</ol>,
                        li: ({children}) => <li className="mb-1">{children}</li>,
                        strong: ({children}) => <strong className="font-semibold">{children}</strong>,
                        em: ({children}) => <em className="italic">{children}</em>,
                        code: ({children}) => <code className="chat-code">{children}</code>,
                        a: ({href, children}) => <a href={href} className="underline hover:opacity-80">{children}</a>,
                      }}
                    >
                      {msg.text}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-sm">{msg.text}</p>
                )}
                {msg.role === 'agent' && (
                  <button
                    type="button"
                    onClick={() => copyMessage(msg.text)}
                    className="copy-button"
                    aria-label="Copy response"
                  >
                    <Copy size={16} strokeWidth={1.5} aria-hidden="true" />
                    Copy
                  </button>
                )}
              </div>
            </div>
          ))}
          {loading && !messages.some(m => m.streaming && m.text) && (
            <div className="chat-message" role="status" aria-live="polite">
              <div className="message-bubble message-agent">
                <span className="text-sm font-medium">
                  {toolActivity ||
                    (executionMode === 'team' ? 'Coordinating team' : 'Running agent')}
                  {elapsed > 0 ? ` · ${elapsed}s` : ''}
                </span>
              </div>
            </div>
          )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Section */}
      <form
        className="surface chat-composer"
        onSubmit={(event) => {
          event.preventDefault()
          if (executionMode === 'single') handleExecuteSingle()
          else handleExecuteTeam()
        }}
      >
        {error && (
          <div className="feedback-error" role="alert">
            {error}
          </div>
        )}
        <div className="chat-composer-row">
          <input
            type="text"
            aria-label="Task prompt"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter your prompt..."
            className="input-primary"
            disabled={loading}
          />
          <Button
            type="submit"
            disabled={
              loading ||
              !input.trim() ||
              (executionMode === 'single' && !selectedAgent) ||
              (executionMode === 'team' && (!selectedHostAgent || selectedMembers.length === 0))
            }
            className="button-primary"
          >
            <Send size={16} strokeWidth={1.5} aria-hidden="true" />
            {loading ? 'Running…' : 'Run'}
          </Button>
          <button
            type="button"
            onClick={() => setMessages([])}
            className="icon-button"
            aria-label="Clear conversation"
            title="Clear conversation"
            disabled={loading || messages.length === 0}
          >
            <Trash2 size={16} strokeWidth={1.5} aria-hidden="true" />
          </button>
        </div>
      </form>
    </div>
  )
}

export default ChatPlayground
