import React, { useEffect, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  CircularProgress,
  Divider,
  Chip,
  Stack,
  Avatar,
  IconButton,
  Paper,
  Tabs,
  Tab,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import CloseIcon from '@mui/icons-material/Close';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import SettingsIcon from '@mui/icons-material/Settings';
import InfoIcon from '@mui/icons-material/Info';
import HistoryIcon from '@mui/icons-material/History';
import ChatIcon from '@mui/icons-material/Chat';
import { agentService } from '../services/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`agent-detail-tabpanel-${index}`}
      aria-labelledby={`agent-detail-tab-${index}`}
      {...other}
      style={{ padding: '16px 0' }}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

interface AgentDetailModalProps {
  open: boolean;
  onClose: () => void;
  agentId: string | null;
  onStartChat?: (agentId: string) => void;
}

const AgentDetailModal: React.FC<AgentDetailModalProps> = ({ open, onClose, agentId, onStartChat }) => {
  const [agent, setAgent] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    if (open && agentId) {
      fetchAgentDetails(agentId);
    }
  }, [open, agentId]);

  const fetchAgentDetails = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const agentData = await agentService.getAgentById(id);
      setAgent(agentData);
    } catch (error: any) {
      console.error('Failed to fetch agent details:', error);
      setError(error?.response?.data?.detail || 'Failed to load agent details');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // Generate random background color for agent avatar
  const getRandomColor = (agentName: string = '') => {
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

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="md" 
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
          boxShadow: 24,
        }
      }}
    >
      <DialogTitle sx={{ 
        p: 3, 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        bgcolor: 'primary.light',
        color: 'white'
      }}>
        <Typography variant="h6" component="div">
          Agent Details
        </Typography>
        <IconButton 
          edge="end" 
          color="inherit" 
          onClick={onClose} 
          aria-label="close"
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 0 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4, minHeight: 300 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Box sx={{ p: 3, textAlign: 'center', minHeight: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Typography color="error" variant="h6">
              {error}
            </Typography>
          </Box>
        ) : agent ? (
          <Box>
            {/* Agent Header */}
            <Box sx={{ p: 3, borderBottom: 1, borderColor: 'divider' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Avatar 
                  sx={{ 
                    bgcolor: getRandomColor(agent.name),
                    width: 60,
                    height: 60,
                    mr: 2
                  }}
                >
                  <SmartToyIcon fontSize="large" />
                </Avatar>
                <Box>
                  <Typography variant="h5" fontWeight={500}>
                    {agent.name}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5, gap: 1 }}>
                    <Chip 
                      size="small" 
                      label={agent.is_mcp ? "MCP Enabled" : "Standard Agent"} 
                      color={agent.is_mcp ? "success" : "primary"} 
                      variant="outlined" 
                    />
                    <Typography variant="body2" color="text.secondary">
                      ID: {agent.id}
                    </Typography>
                  </Box>
                </Box>
              </Box>
              
              {agent.description && (
                <Typography variant="body1" sx={{ mt: 2 }}>
                  {agent.description}
                </Typography>
              )}
            </Box>

            {/* Tabs for different sections */}
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs 
                value={tabValue} 
                onChange={handleTabChange} 
                aria-label="agent detail tabs"
                variant="fullWidth"
              >
                <Tab icon={<InfoIcon />} label="Overview" id="agent-detail-tab-0" />
                <Tab icon={<SettingsIcon />} label="Configuration" id="agent-detail-tab-1" />
                <Tab icon={<HistoryIcon />} label="History" id="agent-detail-tab-2" />
              </Tabs>
            </Box>

            <Box sx={{ p: 3 }}>              <TabPanel value={tabValue} index={0}>
                <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
                  <Box sx={{ width: { xs: '100%', md: '50%' } }}>
                    <Paper elevation={1} sx={{ p: 2, borderRadius: 2, height: '100%' }}>
                      <Typography variant="subtitle1" fontWeight={500} gutterBottom>
                        Capabilities
                      </Typography>
                      <Box sx={{ mt: 1 }}>
                        {agent.is_mcp ? (
                          <Typography variant="body2">
                            This agent has MCP (Model Context Protocol) capabilities, allowing it to interact with external tools and services.
                          </Typography>
                        ) : (
                          <Typography variant="body2">
                            This is a standard agent with text-based interactions only.
                          </Typography>
                        )}
                      </Box>
                    </Paper>
                  </Box>
                  <Box sx={{ width: { xs: '100%', md: '50%' } }}>
                    <Paper elevation={1} sx={{ p: 2, borderRadius: 2, height: '100%' }}>
                      <Typography variant="subtitle1" fontWeight={500} gutterBottom>
                        Parameters
                      </Typography>                      {agent.parameters && agent.parameters.length > 0 ? (
                        <Box sx={{ mt: 1 }}>
                          {agent.parameters.map((param: any, index: number) => (
                            <Box key={index} sx={{ mb: 1 }}>
                              <Typography variant="body2" fontWeight={500}>
                                {param.name}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {param.description || 'No description available'}
                              </Typography>
                            </Box>
                          ))}
                        </Box>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          No parameters defined for this agent.
                        </Typography>
                      )}
                    </Paper>
                  </Box>
                </Stack>
              </TabPanel>
              <TabPanel value={tabValue} index={1}>
                <Paper elevation={1} sx={{ p: 2, borderRadius: 2 }}>
                  <Typography variant="subtitle1" fontWeight={500} gutterBottom>
                    Agent Configuration
                  </Typography>
                  <Box 
                    component="pre" 
                    sx={{ 
                      mt: 2,
                      p: 2,
                      bgcolor: '#f5f5f5',
                      borderRadius: 1,
                      overflow: 'auto',
                      fontSize: '0.875rem',
                      maxHeight: 300
                    }}
                  >
                    {JSON.stringify(agent.config, null, 2)}
                  </Box>
                </Paper>
              </TabPanel>
              <TabPanel value={tabValue} index={2}>
                <Paper elevation={1} sx={{ p: 2, borderRadius: 2 }}>
                  <Typography variant="subtitle1" fontWeight={500} gutterBottom>
                    Interaction History
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                    Agent interaction history is not available in this version.
                  </Typography>
                </Paper>
              </TabPanel>
            </Box>
          </Box>
        ) : (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body1">
              No agent selected. Please select an agent to view details.
            </Typography>
          </Box>
        )}
      </DialogContent>      <DialogActions sx={{ p: 2 }}>
        <Button 
          variant="outlined" 
          onClick={onClose}
        >
          Close
        </Button>
        {agent && (
          <Button 
            variant="contained" 
            color="primary"
            onClick={() => {
              if (agentId && onStartChat) {
                onStartChat(agentId);
              }
              onClose();
            }}
            startIcon={<ChatIcon />}
          >
            Start Chat
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default AgentDetailModal;
