import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Avatar,
  CardActionArea,
  Chip,
  Button,
  Stack,
  IconButton
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ChatIcon from '@mui/icons-material/Chat';
import { agentService } from '../services/api';
import AgentDetailModal from './AgentDetailModal';

interface Agent {
  id: string;
  name: string;
  description?: string;
}

interface AgentComponentProps {
  onAgentSelect?: (agentId: string) => void;
}

const AgentComponent: React.FC<AgentComponentProps> = ({ onAgentSelect }) => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [detailAgentId, setDetailAgentId] = useState<string | null>(null);

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const agentsData = await agentService.getAgents();
      if (Array.isArray(agentsData)) {
        setAgents(agentsData);
      } else {
        // Handle case when API returns an error object
        setError(agentsData.error || 'Failed to fetch agents');
        setAgents([]);
      }
    } catch (error) {
      console.error('Failed to fetch agents:', error);
      setError('Failed to load agents. Please try again later.');
      setAgents([]);    } finally {
      setLoading(false);
    }
  };
  const handleAgentSelect = (agentId: string, event?: React.MouseEvent) => {
    // Stop propagation and prevent default if event is provided
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }
    
    setSelectedAgentId(agentId);
    // If a callback was provided, call it with the selected agent ID
    if (onAgentSelect) {
      onAgentSelect(agentId);
    }
  };

  const handleViewAgentDetails = (agentId: string) => {
    // Open the modal directly
    setDetailAgentId(agentId);
    setDetailModalOpen(true);
  };

  const handleCloseDetailModal = () => {
    setDetailModalOpen(false);
  };

  // Generate random background color for agent avatars
  const getRandomColor = (agentName: string) => {
    const colors = [
      '#1976d2', // blue
      '#388e3c', // green
      '#d32f2f', // red
      '#f57c00', // orange
      '#7b1fa2', // purple
      '#0097a7', // teal
      '#c2185b', // pink
      '#689f38', // light green
      '#5d4037', // brown
    ];
    
    // Use agent name to pick a consistent color
    const index = agentName.length % colors.length;
    return colors[index];
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="error" variant="h6">
          {error}
        </Typography>
        <Typography variant="body2" sx={{ mt: 1 }}>
          Please try again later or contact support.
        </Typography>
      </Box>
    );
  }

  if (agents.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h6">No Agents Available</Typography>
        <Typography variant="body2" sx={{ mt: 1 }}>
          There are currently no agents configured in the system.
        </Typography>
      </Box>
    );
  }
  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
        Available Agents
      </Typography>
      
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>        {agents.map((agent) => (
          <Card 
            key={agent.id}
            sx={{ 
              mb: 1,
              border: agent.id === selectedAgentId ? '2px solid' : '1px solid',
              borderColor: agent.id === selectedAgentId ? 'primary.main' : 'divider',
              boxShadow: agent.id === selectedAgentId ? 3 : 1,
              cursor: 'pointer',
              '&:hover': {
                boxShadow: 3,
              }
            }}
            onClick={() => handleViewAgentDetails(agent.id)}
          >
            <CardContent sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Avatar 
                    sx={{ 
                      bgcolor: getRandomColor(agent.name),
                      mr: 2
                    }}
                  >
                    <SmartToyIcon />
                  </Avatar>
                  <Box>
                    <Typography variant="subtitle1" fontWeight={500}>
                      {agent.name}
                    </Typography>
                    {agent.description && (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                        {agent.description.length > 60 
                          ? `${agent.description.substring(0, 60)}...` 
                          : agent.description}
                      </Typography>
                    )}
                  </Box>
                </Box>
                <Button
                  variant="outlined"
                  color="primary"
                  size="small"
                  startIcon={<ChatIcon />}
                  onClick={(e) => handleAgentSelect(agent.id, e)}
                  sx={{ ml: 1 }}
                >
                  Start Chat
                </Button>
              </Box>
              
              {agent.id === selectedAgentId && (
                <Box sx={{ mt: 1, display: 'flex', justifyContent: 'flex-end' }}>
                  <Chip 
                    size="small" 
                    label="Selected" 
                    color="primary" 
                    variant="outlined" 
                  />
                </Box>
              )}
            </CardContent>
          </Card>
        ))}
      </Box>      {/* Agent Detail Modal */}
      <AgentDetailModal 
        open={detailModalOpen} 
        onClose={handleCloseDetailModal} 
        agentId={detailAgentId}
        onStartChat={handleAgentSelect} 
      />
    </Box>
  );
};

export default AgentComponent;
