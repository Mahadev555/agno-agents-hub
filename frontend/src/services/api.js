import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

// CRUD calls are fast. Agent execution is not: a coordinated team run routinely
// takes 20-60s because it is several sequential LLM calls. A single 30s timeout
// aborted those runs client-side while the backend kept burning tokens.
const CRUD_TIMEOUT = 15000
const EXECUTION_TIMEOUT = 300000

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: CRUD_TIMEOUT,
})

/**
 * Turn an axios failure into a message worth showing a user.
 *
 * The API returns FastAPI error bodies: `detail` is a string for raised
 * HTTPExceptions (404/400/502) and an array of validation objects for 422.
 * Without this, everything surfaced as "Request failed with status code 500".
 */
const extractErrorMessage = (error) => {
  if (error.code === 'ECONNABORTED') {
    return 'The request timed out. The agent may still be running on the server.'
  }

  if (!error.response) {
    return `Cannot reach the API at ${API_BASE_URL}. Is the backend running?`
  }

  const { detail } = error.response.data || {}

  if (typeof detail === 'string') return detail

  // FastAPI 422: [{ loc: ['body','prompt'], msg: '...', type: '...' }, ...]
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc)
          ? item.loc.filter((part) => part !== 'body').join('.')
          : ''
        return field ? `${field}: ${item.msg}` : item.msg
      })
      .join('; ')
  }

  if (detail) return JSON.stringify(detail)

  return error.message || `Request failed with status ${error.response.status}`
}

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = extractErrorMessage(error)
    console.error('API Error:', error.response?.status ?? '', message)

    const normalized = new Error(message)
    normalized.status = error.response?.status
    normalized.original = error
    return Promise.reject(normalized)
  }
)

/**
 * Unwrap an execution response.
 *
 * The API can report failure two ways: a non-2xx status (handled by the
 * interceptor) or a 200 carrying status: "error" when the run itself failed
 * partway. The second kind used to be rendered as an empty reply.
 */
const unwrapExecution = (data) => {
  if (data?.status === 'error') {
    throw new Error(data.message || 'Agent execution failed')
  }
  return data
}

// API Services
export const agentService = {
  getAgents: async () => {
    const response = await api.get('/api/agents')
    return response.data || []
  },

  getHostAgents: async () => {
    const response = await api.get('/api/host-agents')
    return response.data || []
  },

  getAgentById: async (agentId) => {
    const response = await api.get(`/api/agents/${agentId}`)
    return response.data
  },

  executeSingleAgent: async (agentId, prompt) => {
    const response = await api.post(
      '/api/agent/run',
      { agentId: Number(agentId), prompt },
      { timeout: EXECUTION_TIMEOUT }
    )
    return unwrapExecution(response.data)
  },

  executeTeam: async (hostAgentId, memberAgentIds, prompt) => {
    const response = await api.post(
      '/api/team/run',
      {
        hostAgentId: Number(hostAgentId),
        memberAgentIds: memberAgentIds.map(Number),
        prompt,
      },
      { timeout: EXECUTION_TIMEOUT }
    )
    return unwrapExecution(response.data)
  },

  sendMessage: async (prompt, agentIds = [], hostAgentId = null) => {
    const payload = { prompt }
    if (agentIds.length > 0) payload.agentIds = agentIds.map(Number)
    if (hostAgentId) payload.hostAgentId = Number(hostAgentId)

    const response = await api.post('/api/chat', payload, { timeout: EXECUTION_TIMEOUT })
    return unwrapExecution(response.data)
  },

  createAgent: async (agentData) => {
    const response = await api.post('/api/agents', agentData)
    return response.data
  },
}

/**
 * Streaming run API.
 *
 * Preferred over the blocking execute* calls: the server keeps working even if
 * this client goes away, and output arrives token by token instead of after a
 * multi-minute silence.
 */
export const runService = {
  // Returns the pending run record immediately; work continues server-side.
  start: async (prompt, { agentIds = [], hostAgentId = null } = {}) => {
    const payload = { prompt }
    if (agentIds.length > 0) payload.agentIds = agentIds.map(Number)
    if (hostAgentId) payload.hostAgentId = Number(hostAgentId)

    const response = await api.post('/api/runs', payload)
    return response.data
  },

  get: async (runId) => {
    const response = await api.get(`/api/runs/${runId}`)
    return response.data
  },

  list: async (limit = 50) => {
    const response = await api.get('/api/runs', { params: { limit } })
    return response.data || []
  },

  /**
   * Subscribe to a run's events.
   *
   * The server replays everything already emitted before going live, so
   * subscribing a moment after start() still yields the full output.
   *
   * @returns {() => void} cancel function that closes the stream.
   */
  stream: (runId, { onEvent, onDone, onError } = {}) => {
    const source = new EventSource(`${API_BASE_URL}/api/runs/${runId}/events`)
    let settled = false

    const finish = (fn, arg) => {
      if (settled) return
      settled = true
      source.close()
      fn?.(arg)
    }

    source.onmessage = (message) => {
      let event
      try {
        event = JSON.parse(message.data)
      } catch {
        return
      }

      onEvent?.(event)

      // Terminal events are always last. Close explicitly, otherwise
      // EventSource reconnects and replays the whole run.
      if (event.type === 'completed') finish(onDone, event)
      else if (event.type === 'error') finish(onError, new Error(event.message))
    }

    source.onerror = () => {
      // Fires on network drop, and also on normal server-side close if we did
      // not already settle.
      finish(onError, new Error('Connection to the run stream was lost'))
    }

    return () => finish(() => {})
  },
}

export default api
