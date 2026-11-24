/**
 * @typedef {'simple' | 'mcp' | 'host'} AgentType
 * @typedef {Record<string, unknown> & {
 *   kind?: string,
 *   agent_type?: string,
 *   is_mcp?: boolean,
 *   mode?: string
 * }} AgentRecord
 */

/** @type {Readonly<{ INDIVIDUAL: AgentType, MCP: AgentType, COORDINATOR: AgentType }>} */
export const AGENT_TYPES = Object.freeze({
  INDIVIDUAL: 'simple',
  MCP: 'mcp',
  COORDINATOR: 'host',
})

/** @type {Readonly<Record<AgentType, string>>} */
export const AGENT_TYPE_LABELS = Object.freeze({
  simple: 'Individual',
  mcp: 'MCP',
  host: 'Coordinator',
})

const coordinatorModes = new Set(['coordinate', 'route', 'collaborate'])

/** @param {AgentRecord | null | undefined} agent */
export const getAgentType = (agent) => {
  const kind = agent?.kind || agent?.agent_type
  if (
    kind === AGENT_TYPES.COORDINATOR
    || (typeof agent?.mode === 'string' && coordinatorModes.has(agent.mode))
  ) {
    return AGENT_TYPES.COORDINATOR
  }
  if (kind === AGENT_TYPES.MCP || agent?.is_mcp === true) {
    return AGENT_TYPES.MCP
  }
  return AGENT_TYPES.INDIVIDUAL
}

/** @param {AgentRecord | null | undefined} agent */
export const getAgentTypeLabel = (agent) => AGENT_TYPE_LABELS[getAgentType(agent)]

/** @param {AgentRecord[]} agents */
export const countAgentsByType = (agents) => {
  const counts = { simple: 0, mcp: 0, host: 0 }
  agents.forEach((agent) => {
    counts[getAgentType(agent)] += 1
  })
  return counts
}

/** @param {AgentRecord | null | undefined} agent */
export const isCoordinatorAgent = (agent) =>
  getAgentType(agent) === AGENT_TYPES.COORDINATOR
