import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Info, Play } from 'lucide-react'
import { agentService } from '../services/api'
import Button from './Button'

const AgentComponent = () => {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [showModal, setShowModal] = useState(false)

  useEffect(() => {
    fetchAgents()
  }, [])

  const fetchAgents = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await agentService.getAgents()
      setAgents(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch agents:', err)
      setError('Failed to load agents')
    } finally {
      setLoading(false)
    }
  }

  // Get emoji from agent data or use default
  const getAgentEmoji = (agent) => agent.emoji || '🤖'

  // Get color from agent data or use default
  const getAgentColor = (agent) => agent.color || 'from-primary-500 to-primary-600'

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  }

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-4xl font-bold gradient-text">Agents</h1>
        <p className="text-slate-600 mt-2">Discover and manage AI agents</p>
      </motion.div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin">
            <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-500 rounded-full"></div>
          </div>
        </div>
      ) : error ? (
        <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      ) : agents.length === 0 ? (
        <div className="p-6 bg-blue-50 border border-blue-200 rounded-lg text-blue-700">
          No agents available
        </div>
      ) : (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {agents.map(agent => (
            <motion.div key={agent.agent_id} variants={itemVariants}>
              <div className={`card p-6 card-hover bg-gradient-to-br ${getAgentColor(agent)} bg-opacity-5`}>
                <div className="flex justify-between items-start mb-4">
                  <div className={`text-5xl`}>
                    {getAgentEmoji(agent)}
                  </div>
                  <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-full">
                    {agent.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                <h3 className="font-bold text-xl mb-2">{agent.name}</h3>

                {agent.role && (
                  <p className="text-xs text-slate-600 mb-3">
                    <span className="font-semibold">Role:</span> {agent.role}
                  </p>
                )}

                <p className="text-slate-600 text-sm mb-4 line-clamp-3">
                  {agent.description || 'No description available'}
                </p>

                {agent.tools && agent.tools.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs font-semibold text-slate-700 mb-2">Tools:</p>
                    <div className="flex flex-wrap gap-1">
                      {agent.tools.map((tool, i) => (
                        <span
                          key={i}
                          className="px-2.5 py-1 bg-slate-200 text-slate-700 text-xs rounded-lg font-medium"
                        >
                          {tool}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex gap-2 mt-6 pt-4 border-t border-slate-200">
                  <Button
                    variant="primary"
                    size="sm"
                    fullWidth
                    onClick={() => {
                      setSelectedAgent(agent)
                      setShowModal(true)
                    }}
                    className="flex items-center justify-center gap-1"
                  >
                    <Play size={16} />
                    Execute
                  </Button>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    onClick={() => {
                      setSelectedAgent(agent)
                      setShowModal(true)
                    }}
                    className="flex-1 p-1.5 hover:bg-slate-200 rounded-lg transition-colors"
                  >
                    <Info size={18} className="mx-auto" />
                  </motion.button>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Detail Modal */}
      <AnimatePresence>
        {showModal && selectedAgent && (
          <motion.div
            key="agent-modal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowModal(false)}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="card max-w-md w-full p-6"
            >
              <div className="text-4xl mb-4">{getAgentEmoji(selectedAgent)}</div>
              <h2 className="text-2xl font-bold mb-4">{selectedAgent.name}</h2>

              <div className="space-y-4 mb-6">
                <div>
                  <h3 className="font-semibold text-slate-700 mb-1">Description</h3>
                  <p className="text-slate-600 text-sm">{selectedAgent.description || 'No description'}</p>
                </div>

                {selectedAgent.agent_type && (
                  <div>
                    <h3 className="font-semibold text-slate-700 mb-1">Type</h3>
                    <p className="inline-block px-3 py-1 bg-slate-200 text-slate-700 text-xs rounded-lg font-medium">
                      {selectedAgent.agent_type}
                    </p>
                  </div>
                )}

                {selectedAgent.config?.instructions && (
                  <div>
                    <h3 className="font-semibold text-slate-700 mb-1">Instructions</h3>
                    <p className="text-slate-600 text-sm line-clamp-3">{selectedAgent.config.instructions}</p>
                  </div>
                )}

                <div className="p-4 bg-slate-100 rounded-lg">
                  <p className="text-xs text-slate-700 font-mono">
                    ID: {selectedAgent.agent_id}
                  </p>
                  <p className="text-xs text-slate-700 font-mono mt-1">
                    Status: {selectedAgent.is_active ? 'Active' : 'Inactive'}
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <Button variant="secondary" size="md" fullWidth onClick={() => setShowModal(false)}>
                  Close
                </Button>
                <Button variant="primary" size="md" fullWidth onClick={() => setShowModal(false)}>
                  Execute
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default AgentComponent
