import { useCallback, useEffect, useState } from 'react'
import {
  agentService,
  buildLatestRunByAgent,
  isCoordinatorAgent,
  runService,
} from '../services/api'

export const useAgentCatalog = (refreshKey = 0) => {
  const [agents, setAgents] = useState([])
  const [hostAgents, setHostAgents] = useState([])
  const [lastRuns, setLastRuns] = useState({})
  const [runHistoryError, setRunHistoryError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [agentsData, hostAgentsData] = await Promise.all([
        agentService.getAgents(),
        agentService.getHostAgents(),
      ])
      setAgents(Array.isArray(agentsData) ? agentsData.filter(agent => !isCoordinatorAgent(agent)) : [])
      setHostAgents(Array.isArray(hostAgentsData) ? hostAgentsData : [])

      let historyLoaded = true
      try {
        const runs = await runService.list(200)
        setLastRuns(buildLatestRunByAgent(Array.isArray(runs) ? runs : []))
        setRunHistoryError(null)
      } catch {
        setLastRuns({})
        setRunHistoryError('Recent run data is unavailable.')
        historyLoaded = false
      }

      return { success: true, historyLoaded }
    } catch (requestError) {
      setError(requestError.message || 'Could not load agents.')
      return { success: false, historyLoaded: false }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh, refreshKey])

  const allAgents = [...agents, ...hostAgents]

  return {
    agents,
    hostAgents,
    allAgents,
    lastRuns,
    runHistoryError,
    loading,
    error,
    refresh,
  }
}
