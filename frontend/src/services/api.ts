import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000'; // Backend server URL

// Create axios instance with base URL
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API Services
export const agentService = {
  // Get all available agents
  getAgents: async () => {
    try {
      const response = await api.get('/api/agents');
      return response.data;
    } catch (error) {
      console.error('Error fetching agents:', error);
      throw error;
    }
  },
  
  // Get details for a specific agent by ID
  getAgentById: async (agentId: string) => {
    try {
      const response = await api.get(`/api/agents/${agentId}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching agent ${agentId}:`, error);
      throw error;
    }
  },
  
  // Execute an agent with specific inputs
  executeAgent: async (agentId: string, input: any) => {
    try {
      const response = await api.post(`/api/execute/${agentId}`, input);
      return response.data;
    } catch (error) {
      console.error('Error executing agent:', error);
      throw error;
    }
  },
  
  // Send a message to the chat
  sendMessage: async (prompt: string, agentIds: string[] = []) => {
    try {
      const response = await api.post('/api/chat', { prompt, agentIds });
      return response.data;
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }
};

export default api;
