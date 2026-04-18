import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  Typography,
  Avatar,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Stack,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import { agentService } from '../services/api';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
}

interface Agent {
  id: string;
  name: string;
  description?: string;
}

interface ChatPlaygroundProps {
  preselectedAgentId?: string | null;
}

const ChatPlayground: React.FC<ChatPlaygroundProps> = ({ preselectedAgentId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentIds, setSelectedAgentIds] = useState<string[]>([]);
  const messagesEndRef = useRef<null | HTMLDivElement>(null);
  // Fetch available agents on component mount
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const agentsData = await agentService.getAgents();
        if (Array.isArray(agentsData)) {
          setAgents(agentsData);
          
          // If we have a preselected agent and it's in the agent list, select it
          if (preselectedAgentId && agentsData.some(agent => agent.id === preselectedAgentId)) {
            setSelectedAgentIds([preselectedAgentId]);
          }
        }
      } catch (error) {
        console.error('Failed to fetch agents:', error);
      }
    };

    fetchAgents();
    
    // Add welcome message
    setMessages([
      {
        id: '0',
        text: 'Hello! How can I assist you today? Select an agent to chat with from the dropdown below.',
        sender: 'agent',        timestamp: new Date(),
      },
    ]);
  }, [preselectedAgentId]);

  // Auto scroll to bottom when messages update
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  const handleAgentChange = (event: SelectChangeEvent<string[]>) => {
    const value = event.target.value;
    setSelectedAgentIds(typeof value === 'string' ? [value] : value);
  };

  const handleSendMessage = async () => {
    if (input.trim() === '') return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: input,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await agentService.sendMessage(input, selectedAgentIds);
      
      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.response || 'Sorry, I could not process your request.',
        sender: 'agent',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, there was an error processing your request. Please try again later.',
        sender: 'agent',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ 
        flexGrow: 1, 
        overflow: 'auto', 
        p: 2,
        backgroundColor: '#f5f7fb',
      }}>
        {messages.map((message) => (
          <Box
            key={message.id}
            sx={{
              display: 'flex',
              justifyContent: message.sender === 'user' ? 'flex-end' : 'flex-start',
              mb: 2,
            }}
          >
            <Box
              sx={{
                display: 'flex',
                flexDirection: message.sender === 'user' ? 'row-reverse' : 'row',
                alignItems: 'flex-start',
                maxWidth: '70%',
              }}
            >
              <Avatar
                sx={{
                  bgcolor: message.sender === 'user' ? 'primary.main' : 'secondary.main',
                  width: 32,
                  height: 32,
                  mx: 1,
                }}
              >
                {message.sender === 'user' ? 'U' : 'A'}
              </Avatar>
              <Paper
                elevation={1}
                sx={{
                  p: 2,
                  borderRadius: 2,
                  bgcolor: message.sender === 'user' ? 'primary.light' : 'white',
                  color: message.sender === 'user' ? 'white' : 'text.primary',
                }}
              >
                <Typography variant="body1">{message.text}</Typography>
                <Typography variant="caption" color={message.sender === 'user' ? 'rgba(255,255,255,0.7)' : 'text.secondary'} sx={{ display: 'block', mt: 1 }}>
                  {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Typography>
              </Paper>
            </Box>
          </Box>
        ))}
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', ml: 5 }}>
              <CircularProgress size={20} />
              <Typography variant="body2" sx={{ ml: 1 }}>
                Thinking...
              </Typography>
            </Box>
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Box>
      
      <Box sx={{ p: 2, backgroundColor: 'background.paper', borderTop: '1px solid rgba(0, 0, 0, 0.12)' }}>
        <FormControl fullWidth variant="outlined" size="small" sx={{ mb: 2 }}>
          <InputLabel id="agent-select-label">Select Agent(s)</InputLabel>
          <Select
            labelId="agent-select-label"
            id="agent-select"
            multiple
            value={selectedAgentIds}
            onChange={handleAgentChange}
            label="Select Agent(s)"
            renderValue={(selected) => {
              const selectedNames = agents
                .filter(agent => selected.includes(agent.id))
                .map(agent => agent.name);
              return selectedNames.join(', ');
            }}
          >
            {agents.map((agent) => (
              <MenuItem key={agent.id} value={agent.id}>
                {agent.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        <Stack direction="row" spacing={2} alignItems="center">
          <Box sx={{ flexGrow: 1 }}>
            <TextField
              fullWidth
              placeholder="Type a message..."
              variant="outlined"
              size="small"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={loading || selectedAgentIds.length === 0}
              multiline
              maxRows={4}
            />
          </Box>
          <Box>
            <IconButton 
              color="primary" 
              onClick={handleSendMessage} 
              disabled={loading || input.trim() === '' || selectedAgentIds.length === 0}
              sx={{
                backgroundColor: 'primary.main',
                color: 'white',
                '&:hover': {
                  backgroundColor: 'primary.dark',
                },
                '&.Mui-disabled': {
                  backgroundColor: 'action.disabledBackground',
                  color: 'action.disabled',
                }
              }}
            >
              <SendIcon />
            </IconButton>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
};

export default ChatPlayground;
