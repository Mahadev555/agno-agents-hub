import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { agentService } from '../services/api'
import Button from './Button'

const Dashboard = () => {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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

  const stats = [
    { label: 'Total Agents', value: agents.length, icon: '🤖', color: 'from-primary-500 to-primary-600' },
    { label: 'Active', value: agents.filter(a => a.status === 'active').length, icon: '✅', color: 'from-emerald-500 to-emerald-600' },
    { label: 'Executions', value: '955', icon: '⚡', color: 'from-amber-500 to-amber-600' },
    { label: 'Avg Response', value: '2.3s', icon: '⏱️', color: 'from-secondary-500 to-secondary-600' },
  ]

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
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-4xl font-bold gradient-text">Dashboard</h1>
        <p className="text-slate-600 mt-2">Manage and monitor your AI agents</p>
      </motion.div>

      {/* Stats Grid */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"
      >
        {stats.map((stat, idx) => (
          <motion.div key={idx} variants={itemVariants}>
            <div className={`card p-6 border-l-4 border-slate-200 hover:border-primary-500`}>
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-slate-600 text-sm font-medium">{stat.label}</p>
                  <p className="text-4xl font-bold mt-2 gradient-text">{stat.value}</p>
                </div>
                <div className="text-3xl">{stat.icon}</div>
              </div>
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* Agents Section */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
        <h2 className="text-2xl font-bold mb-6">Available Agents</h2>

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
            {agents.map((agent, idx) => (
              <motion.div key={agent.agent_id} variants={itemVariants}>
                <div className="card p-6 card-hover">
                  <div className="flex justify-between items-start mb-4">
                    <div className="text-4xl">
                      {agent.emoji || '🤖'}
                    </div>
                    <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-full">
                      {agent.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  
                  <h3 className="font-bold text-lg mb-1">{agent.name}</h3>
                  <p className="text-slate-600 text-sm mb-4 line-clamp-2">{agent.description || 'No description'}</p>
                  
                  {agent.role && (
                    <p className="text-xs text-slate-500 mb-3">Role: {agent.role}</p>
                  )}

                  {agent.tools && agent.tools.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-4">
                      {agent.tools.slice(0, 3).map((tool, i) => (
                        <span key={i} className="px-2 py-1 bg-slate-100 text-slate-700 text-xs rounded">
                          {tool}
                        </span>
                      ))}
                      {agent.tools.length > 3 && (
                        <span className="px-2 py-1 bg-slate-100 text-slate-700 text-xs rounded">
                          +{agent.tools.length - 3}
                        </span>
                      )}
                    </div>
                  )}

                  <div className="flex gap-2 mt-4">
                    <Button variant="primary" size="sm" fullWidth>Execute</Button>
                    <Button variant="outline" size="sm" fullWidth>Details</Button>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </motion.div>
    </div>
  )
}

export default Dashboard
