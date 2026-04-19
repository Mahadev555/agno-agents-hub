import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// API Services
export const agentService = {
  getAgents: async () => {
    try {
      const response = await api.get('/api/agents')
      return response.data || []
    } catch (error) {
      console.error('Error fetching agents:', error)
      throw error
    }
  },

  getHostAgents: async () => {
    try {
      const response = await api.get('/api/host-agents')
      return response.data || []
    } catch (error) {
      console.error('Error fetching host agents:', error)
      throw error
    }
  },

  getAgentById: async (agentId) => {
    try {
      const response = await api.get(`/api/agents/${agentId}`)
      return response.data
    } catch (error) {
      console.error(`Error fetching agent ${agentId}:`, error)
      throw error
    }
  },

  executeSingleAgent: async (agentId, prompt) => {
    try {
      const response = await api.post('/api/agent/run', {
        agentId: agentId,
        prompt: prompt,
      })
      return response.data
    } catch (error) {
      console.error('Error executing single agent:', error)
      throw error
    }
  },

  executeTeam: async (hostAgentId, memberAgentIds, prompt) => {
    try {
      const response = await api.post('/api/team/run', {
        hostAgentId: hostAgentId,
        memberAgentIds: memberAgentIds,
        prompt: prompt,
      })
      return response.data
    } catch (error) {
      console.error('Error executing team:', error)
      throw error
    }
  },

  sendMessage: async (prompt, agentIds = []) => {
    try {
      const payload = agentIds.length > 0 
        ? { prompt, agentIds }
        : { prompt }
      
      const response = await api.post('/api/chat', payload)
      return response.data
    } catch (error) {
      console.error('Error sending message:', error)
      throw error
    }
  },

  executeAgent: async (agentId, input) => {
    try {
      const response = await api.post(`/api/execute/${agentId}`, input)
      return response.data
    } catch (error) {
      console.error('Error executing agent:', error)
      throw error
    }
  },

  createAgent: async (agentData) => {
    try {
      const response = await api.post('/api/agents', agentData)
      return response.data
    } catch (error) {
      console.error('Error creating agent:', error)
      throw error
    }
  },
}

export default api
