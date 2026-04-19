import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Trash2, Copy } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { agentService } from '../services/api'
import Button from './Button'

const ChatPlayground = () => {
  const [agents, setAgents] = useState([])
  const [executionMode, setExecutionMode] = useState('single')
  const [selectedAgent, setSelectedAgent] = useState('')
  const [selectedHostAgent, setSelectedHostAgent] = useState('')
  const [selectedMembers, setSelectedMembers] = useState([])
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    const initializeChat = async () => {
      await fetchAgents()
    }
    initializeChat()
    setMessages([{
      id: Date.now().toString(),
      text: 'Welcome to Agno Hub Chat! Select agents and execute prompts.',
      role: 'system',
      timestamp: new Date(),
    }])
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const fetchAgents = async () => {
    try {
      const data = await agentService.getAgents()
      const agentList = Array.isArray(data) ? data : []
      setAgents(agentList)
      if (agentList.length > 0) {
        setSelectedAgent(agentList[0].agent_id)
        setSelectedHostAgent(agentList[0].agent_id)
      }
    } catch (err) {
      console.error('Failed to fetch agents:', err)
      setError('Failed to load agents')
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const addSystemMessage = (text) => {
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      text,
      role: 'system',
      timestamp: new Date(),
    }])
  }

  const addMessage = (text, role) => {
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      text,
      role,
      timestamp: new Date(),
    }])
  }

  const handleExecuteSingle = async () => {
    if (!input.trim() || !selectedAgent) return

    addMessage(input, 'user')
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const response = await agentService.executeSingleAgent(selectedAgent, input)
      addMessage(response.response || 'No response', 'agent')
    } catch (err) {
      setError('Execution failed')
      addMessage('Error: ' + err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleExecuteTeam = async () => {
    if (!input.trim() || !selectedHostAgent || selectedMembers.length === 0) return

    addMessage(input, 'user')
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const response = await agentService.executeTeam(selectedHostAgent, selectedMembers, input)
      addMessage(response.response || 'Team execution complete', 'agent')
    } catch (err) {
      setError('Team execution failed')
      addMessage('Error: ' + err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  const toggleMember = (agentId) => {
    setSelectedMembers(prev =>
      prev.includes(agentId)
        ? prev.filter(id => id !== agentId)
        : [...prev, agentId]
    )
  }

  const copyMessage = (text) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="space-y-6 h-full flex flex-col">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-4xl font-bold gradient-text">Chat Playground</h1>
        <p className="text-slate-600 mt-2">Execute single or team-based AI operations</p>
      </motion.div>

      {/* Mode Selection */}
      <div className="flex gap-4 border-b border-slate-200 pb-4">
        {['single', 'team'].map(mode => (
          <motion.button
            key={mode}
            whileHover={{ scale: 1.05 }}
            onClick={() => setExecutionMode(mode)}
            className={`px-6 py-2 font-medium rounded-lg transition-all ${
              executionMode === mode
                ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-md'
                : 'text-slate-700 hover:bg-slate-100'
            }`}
          >
            {mode === 'single' ? 'Single Agent' : 'Team Execution'}
          </motion.button>
        ))}
      </div>

      {/* Config Section */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card p-6">
        {executionMode === 'single' ? (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Select Agent</label>
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="input-primary"
            >
              {agents.map(agent => (
                <option key={agent.agent_id} value={agent.agent_id}>
                  {agent.name}{agent.role ? ` (${agent.role})` : ''}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Host Agent</label>
              <select
                value={selectedHostAgent}
                onChange={(e) => setSelectedHostAgent(e.target.value)}
                className="input-primary"
              >
                {agents.map(agent => (
                  <option key={agent.agent_id} value={agent.agent_id}>
                    {agent.name}{agent.role ? ` (${agent.role})` : ''}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Team Members</label>
              <div className="flex flex-wrap gap-2">
                {agents.filter(a => a.agent_id !== selectedHostAgent).map(agent => (
                  <motion.button
                    key={agent.agent_id}
                    whileHover={{ scale: 1.05 }}
                    onClick={() => toggleMember(agent.agent_id)}
                    className={`px-3 py-2 rounded-lg font-medium transition-all ${
                      selectedMembers.includes(agent.agent_id)
                        ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    {agent.name}
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
        )}
      </motion.div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 card p-6">
        <AnimatePresence>
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-xl px-4 py-3 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white'
                  : msg.role === 'system'
                  ? 'bg-slate-100 text-slate-700'
                  : msg.role === 'error'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-slate-200 text-slate-900'
              }`}>
                {msg.role === 'agent' || msg.role === 'system' ? (
                  <div className="text-sm prose prose-sm max-w-none dark:prose-invert">
                    <ReactMarkdown
                      components={{
                        p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                        ul: ({children}) => <ul className="list-disc list-inside mb-2">{children}</ul>,
                        ol: ({children}) => <ol className="list-decimal list-inside mb-2">{children}</ol>,
                        li: ({children}) => <li className="mb-1">{children}</li>,
                        strong: ({children}) => <strong className="font-semibold">{children}</strong>,
                        em: ({children}) => <em className="italic">{children}</em>,
                        code: ({children}) => <code className="bg-black/20 px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>,
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
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    onClick={() => copyMessage(msg.text)}
                    className="mt-2 p-1 hover:bg-white/20 rounded"
                  >
                    <Copy size={14} />
                  </motion.button>
                )}
              </div>
            </motion.div>
          ))}
          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex justify-start"
            >
              <div className="bg-slate-200 text-slate-900 px-4 py-3 rounded-lg flex items-center gap-2">
                <span className="text-sm font-medium"></span>
                <motion.div
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  className="flex gap-1"
                >
                  <div className="w-2 h-2 bg-slate-600 rounded-full" />
                  <div className="w-2 h-2 bg-slate-600 rounded-full" />
                  <div className="w-2 h-2 bg-slate-600 rounded-full" />
                </motion.div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Input Section */}
      <motion.div className="card p-6 space-y-3">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && (executionMode === 'single' ? handleExecuteSingle() : handleExecuteTeam())}
            placeholder="Enter your prompt..."
            className="input-primary flex-1"
            disabled={loading}
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={executionMode === 'single' ? handleExecuteSingle : handleExecuteTeam}
            disabled={loading || !input.trim()}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            <Send size={18} />
            Execute
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            onClick={() => setMessages([])}
            className="p-2.5 hover:bg-slate-200 rounded-lg"
          >
            <Trash2 size={18} />
          </motion.button>
        </div>
      </motion.div>
    </div>
  )
}

export default ChatPlayground
