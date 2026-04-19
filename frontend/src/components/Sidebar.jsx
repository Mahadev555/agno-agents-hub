import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Plus } from 'lucide-react'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { agentService } from '../services/api'
import Button from './Button'

const Sidebar = ({ activeTab, setActiveTab, tabs, isOpen, onClose }) => {
  const isMobile = useMediaQuery('(max-width: 768px)')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createFormData, setCreateFormData] = useState({
    name: '',
    description: '',
    agent_type: 'simple',
    role: '',
    instructions: '',
    modelId: 'gemini-2.5-flash-lite',
    modelType: 'google',
    maxTokens: 4096,
    markdown: true,
    showToolCalls: true,
    tools: [],
    config: {},
  })
  const [isCreating, setIsCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  const sidebarVariants = {
    open: { x: 0, opacity: 1 },
    closed: { x: '-100%', opacity: 0 },
  }

  const handleCreateAgent = async (e) => {
    e.preventDefault()
    if (!createFormData.name.trim()) {
      setCreateError('Agent name is required')
      return
    }

    setIsCreating(true)
    setCreateError('')
    try {
      // Build proper config with all required fields
      const agentConfig = {
        name: createFormData.name,
        role: createFormData.role || 'Assistant',
        description: createFormData.description || '',
        instructions: createFormData.instructions || '',
        tools: createFormData.tools || [],
        markdown: createFormData.markdown,
        show_tool_calls: createFormData.showToolCalls,
        model_config: {
          id: createFormData.modelId,
          type: createFormData.modelType,
          max_tokens: parseInt(createFormData.maxTokens) || 4096,
        },
        additional_params: {},
      }

      const payload = {
        name: createFormData.name,
        description: createFormData.description,
        agent_type: createFormData.agent_type,
        instructions: createFormData.instructions,
        config: agentConfig,
        is_mcp: createFormData.agent_type === 'mcp',
      }

      await agentService.createAgent(payload)
      setCreateFormData({
        name: '',
        description: '',
        agent_type: 'simple',
        role: '',
        instructions: '',
        modelId: 'gemini-2.5-flash-lite',
        modelType: 'google',
        maxTokens: 4096,
        markdown: true,
        showToolCalls: true,
        tools: [],
        config: {},
      })
      setShowCreateModal(false)
    } catch (err) {
      setCreateError(err.message || 'Failed to create agent')
    } finally {
      setIsCreating(false)
    }
  }

  const content = (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="w-72 bg-white border-r border-slate-200 h-full flex flex-col"
    >
      {/* Header */}
      <div className="p-6 border-b border-slate-200">
        <h2 className="text-xl font-bold gradient-text">Navigation</h2>
      </div>

      {/* Tabs */}
      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        {tabs.map((tab) => (
          <motion.button
            key={tab.id}
            whileHover={{ x: 4 }}
            onClick={() => {
              setActiveTab(tab.id)
              if (isMobile) onClose()
            }}
            className={`w-full px-4 py-3 rounded-lg font-medium transition-all text-left flex items-center gap-3 ${
              activeTab === tab.id
                ? 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-md'
                : 'text-slate-700 hover:bg-slate-100'
            }`}
          >
            <span className="text-xl">{tab.icon}</span>
            {tab.label}
          </motion.button>
        ))}
      </nav>

      {/* Create Agent Button */}
      <div className="p-4 border-t border-slate-200">
        <Button
          variant="primary"
          fullWidth
          onClick={() => setShowCreateModal(true)}
          className="flex items-center justify-center gap-2"
        >
          <Plus size={18} />
          Create Agent
        </Button>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-slate-200">
        <div className="p-4 bg-gradient-to-r from-primary-50 to-secondary-50 rounded-lg">
          <p className="text-sm font-medium text-primary-700">Version 1.0.0</p>
          <p className="text-xs text-slate-600 mt-1">AI Agent Platform</p>
        </div>
      </div>
    </motion.div>
  )

  // Desktop Sidebar
  if (!isMobile) {
    return (
      <>
        <AnimatePresence>
          {isOpen && (
            <motion.aside
              variants={sidebarVariants}
              initial="closed"
              animate="open"
              exit="closed"
              transition={{ duration: 0.3 }}
            >
              {content}
            </motion.aside>
          )}
        </AnimatePresence>

        {/* Create Agent Modal */}
        <AnimatePresence>
          {showCreateModal && (
            <motion.div
              key="create-agent-modal"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowCreateModal(false)}
              className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="card max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto"
              >
                <h2 className="text-2xl font-bold mb-6">Create New Agent</h2>

                <form onSubmit={handleCreateAgent} className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Agent Name *
                    </label>
                    <input
                      type="text"
                      value={createFormData.name}
                      onChange={(e) => setCreateFormData({ ...createFormData, name: e.target.value })}
                      className="input-primary"
                      placeholder="Enter agent name"
                      required
                    />
                  </div>

                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Description
                    </label>
                    <textarea
                      value={createFormData.description}
                      onChange={(e) => setCreateFormData({ ...createFormData, description: e.target.value })}
                      className="input-primary"
                      placeholder="Enter agent description"
                      rows="2"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Agent Type
                    </label>
                    <select
                      value={createFormData.agent_type}
                      onChange={(e) => setCreateFormData({ ...createFormData, agent_type: e.target.value })}
                      className="input-primary"
                    >
                      <option value="simple">Simple</option>
                      <option value="mcp">MCP</option>
                      <option value="host">Host</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Role
                    </label>
                    <input
                      type="text"
                      value={createFormData.role}
                      onChange={(e) => setCreateFormData({ ...createFormData, role: e.target.value })}
                      className="input-primary"
                      placeholder="e.g., Data Analyst"
                    />
                  </div>

                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      System Instructions
                    </label>
                    <textarea
                      value={createFormData.instructions}
                      onChange={(e) => setCreateFormData({ ...createFormData, instructions: e.target.value })}
                      className="input-primary"
                      placeholder="Enter system instructions for the agent"
                      rows="3"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Model ID
                    </label>
                    <input
                      type="text"
                      value={createFormData.modelId}
                      onChange={(e) => setCreateFormData({ ...createFormData, modelId: e.target.value })}
                      className="input-primary"
                      placeholder="gemini-2.5-flash-lite"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Model Type
                    </label>
                    <select
                      value={createFormData.modelType}
                      onChange={(e) => setCreateFormData({ ...createFormData, modelType: e.target.value })}
                      className="input-primary"
                    >
                      <option value="google">Google</option>
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      Max Tokens
                    </label>
                    <input
                      type="number"
                      value={createFormData.maxTokens}
                      onChange={(e) => setCreateFormData({ ...createFormData, maxTokens: e.target.value })}
                      className="input-primary"
                      placeholder="4096"
                      min="100"
                      max="32000"
                    />
                  </div>

                  <div className="col-span-2 flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={createFormData.markdown}
                        onChange={(e) => setCreateFormData({ ...createFormData, markdown: e.target.checked })}
                        className="w-4 h-4"
                      />
                      <span className="text-sm font-medium text-slate-700">Markdown</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={createFormData.showToolCalls}
                        onChange={(e) => setCreateFormData({ ...createFormData, showToolCalls: e.target.checked })}
                        className="w-4 h-4"
                      />
                      <span className="text-sm font-medium text-slate-700">Show Tool Calls</span>
                    </label>
                  </div>

                  {createError && (
                    <div className="col-span-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                      {createError}
                    </div>
                  )}

                  <div className="col-span-2 flex gap-2 pt-4">
                    <Button
                      variant="secondary"
                      fullWidth
                      onClick={() => setShowCreateModal(false)}
                      type="button"
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      fullWidth
                      type="submit"
                      disabled={isCreating}
                    >
                      {isCreating ? 'Creating...' : 'Create'}
                    </Button>
                  </div>
                </form>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </>
    )
  }

  // Mobile Sidebar (Drawer)
  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm"
            />
            <motion.aside
              variants={sidebarVariants}
              initial="closed"
              animate="open"
              exit="closed"
              transition={{ duration: 0.3 }}
              className="fixed left-0 top-0 bottom-0 z-40"
            >
              <div className="relative">
                {content}
                <motion.button
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={onClose}
                  className="absolute top-6 right-6 p-2 hover:bg-slate-100 rounded-lg"
                >
                  <X size={24} />
                </motion.button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Create Agent Modal */}
      <AnimatePresence>
        {showCreateModal && (
          <motion.div
            key="create-agent-modal-mobile"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowCreateModal(false)}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="card max-w-xl w-full flex flex-col max-h-[90vh]"
            >
              <div className="flex justify-between items-center mb-6 p-6 pb-0">
                <h2 className="text-2xl font-bold">Create New Agent</h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                  type="button"
                >
                  <X className="w-6 h-6 text-slate-600" />
                </button>
              </div>

              <form onSubmit={handleCreateAgent} className="grid grid-cols-1 sm:grid-cols-2 gap-4 overflow-y-auto px-6 pb-6 flex-1">
                <div className="col-span-full">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Agent Name *
                  </label>
                  <input
                    type="text"
                    value={createFormData.name}
                    onChange={(e) => setCreateFormData({ ...createFormData, name: e.target.value })}
                    className="input-primary"
                    placeholder="Enter agent name"
                    required
                  />
                </div>

                <div className="col-span-full">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Description
                  </label>
                  <textarea
                    value={createFormData.description}
                    onChange={(e) => setCreateFormData({ ...createFormData, description: e.target.value })}
                    className="input-primary"
                    placeholder="Enter agent description"
                    rows="2"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Agent Type
                  </label>
                  <select
                    value={createFormData.agent_type}
                    onChange={(e) => setCreateFormData({ ...createFormData, agent_type: e.target.value })}
                    className="input-primary"
                  >
                    <option value="simple">Simple</option>
                    <option value="mcp">MCP</option>
                    <option value="host">Host</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Role
                  </label>
                  <input
                    type="text"
                    value={createFormData.role}
                    onChange={(e) => setCreateFormData({ ...createFormData, role: e.target.value })}
                    className="input-primary"
                    placeholder="e.g., Data Analyst"
                  />
                </div>

                <div className="col-span-full">
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    System Instructions
                  </label>
                  <textarea
                    value={createFormData.instructions}
                    onChange={(e) => setCreateFormData({ ...createFormData, instructions: e.target.value })}
                    className="input-primary"
                    placeholder="Enter system instructions for the agent"
                    rows="3"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Model ID
                  </label>
                  <input
                    type="text"
                    value={createFormData.modelId}
                    onChange={(e) => setCreateFormData({ ...createFormData, modelId: e.target.value })}
                    className="input-primary"
                    placeholder="gemini-2.5-flash-lite"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Model Type
                  </label>
                  <select
                    value={createFormData.modelType}
                    onChange={(e) => setCreateFormData({ ...createFormData, modelType: e.target.value })}
                    className="input-primary"
                  >
                    <option value="google">Google</option>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Max Tokens
                  </label>
                  <input
                    type="number"
                    value={createFormData.maxTokens}
                    onChange={(e) => setCreateFormData({ ...createFormData, maxTokens: e.target.value })}
                    className="input-primary"
                    placeholder="4096"
                    min="100"
                    max="32000"
                  />
                </div>

                <div className="col-span-full flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={createFormData.markdown}
                      onChange={(e) => setCreateFormData({ ...createFormData, markdown: e.target.checked })}
                      className="w-4 h-4"
                    />
                    <span className="text-sm font-medium text-slate-700">Markdown</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={createFormData.showToolCalls}
                      onChange={(e) => setCreateFormData({ ...createFormData, showToolCalls: e.target.checked })}
                      className="w-4 h-4"
                    />
                    <span className="text-sm font-medium text-slate-700">Show Tool Calls</span>
                  </label>
                </div>

                {createError && (
                  <div className="col-span-full p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                    {createError}
                  </div>
                )}

                <div className="col-span-full flex gap-2 pt-4">
                  <Button
                    variant="secondary"
                    fullWidth
                    onClick={() => setShowCreateModal(false)}
                    type="button"
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    fullWidth
                    type="submit"
                    disabled={isCreating}
                  >
                    {isCreating ? 'Creating...' : 'Create'}
                  </Button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

export default Sidebar
