import React, { useState } from "react";
import { Box, Tabs, Tab, Paper, Typography, Stack } from "@mui/material";
import { styled } from "@mui/material/styles";
import ChatPlayground from "./ChatPlayground";
import AgentComponent from "./AgentComponent";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import ChatIcon from "@mui/icons-material/Chat";
import DashboardIcon from "@mui/icons-material/Dashboard";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel = (props: TabPanelProps) => {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      style={{ height: "100%", overflow: "auto", width: "100%" }}
      {...other}
    >
      {value === index && (
        <Box sx={{ height: "100%", width: "100%" }}>
          {children}
        </Box>
      )}
    </div>
  );
};

const StyledVerticalTabs = styled(Tabs)(({ theme }) => ({
  borderRight: `1px solid ${theme.palette.divider}`,
  "& .MuiTabs-indicator": {
    backgroundColor: theme.palette.primary.main,
    right: 0,
    left: "auto",
    width: 3,
  },
  "& .MuiTab-root": {
    minWidth: "60px",
    width: "60px",
    minHeight: "60px",
    marginBottom: theme.spacing(1),
    borderRadius: theme.spacing(1),
    "&.Mui-selected": {
      color: theme.palette.primary.main,
      backgroundColor: theme.palette.action.selected,
    },
  },
}));

const StyledTab = styled(Tab)(({ theme }) => ({
  textTransform: "none",
  fontWeight: 500,
  fontSize: "1rem",
  color: theme.palette.text.secondary,
  "&.Mui-selected": {
    color: theme.palette.primary.main,
    fontWeight: 600,
  },
}));

const MainLayout: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleAgentSelect = (agentId: string) => {
    setSelectedAgentId(agentId);
    // Switch to the playground tab after selecting an agent
    setTabValue(2);
  };

  // Fixed sidebar width
  const sidebarWidth = "80px";

  return (
    <Box sx={{ 
      display: "flex", 
      height: "calc(100vh - 64px)",
    }}>
      {/* Vertical Sidebar - fixed width */}
      <Box
        component="nav"
        sx={{
          width: sidebarWidth,
          flexShrink: 0,
          borderRight: "1px solid rgba(0, 0, 0, 0.12)",
          backgroundColor: "#f5f7fb",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          paddingTop: 2,
        }}
      >
        <StyledVerticalTabs
          value={tabValue}
          onChange={handleTabChange}
          aria-label="sidebar tabs"
          orientation="vertical"
        >
          <StyledTab 
            icon={<DashboardIcon />}
            id="tab-0" 
            aria-controls="tabpanel-0"
            sx={{ mb: 1 }}
          />
          <StyledTab 
            icon={<SmartToyIcon />}
            id="tab-1" 
            aria-controls="tabpanel-1"
            sx={{ mb: 1 }}
          />
          <StyledTab 
            icon={<ChatIcon />}
            id="tab-2" 
            aria-controls="tabpanel-2"
          />
        </StyledVerticalTabs>
      </Box>

      {/* Main content area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: `calc(100% - ${sidebarWidth})`,
          height: "100%",
          backgroundColor: "#f5f7fb",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Content Panels */}
        <TabPanel value={tabValue} index={0}>
          <Box sx={{ p: 3, height: "100%" }}>
            <Typography variant="h4" gutterBottom>
              agno_hub Hub Dashboard
            </Typography>
            <Typography variant="subtitle1" gutterBottom>
              Welcome to Agno Hub - Your AI Agent Management System
            </Typography>
            
            <Stack direction="row" spacing={2} sx={{ mt: 4 }}>
              <Paper 
                elevation={1} 
                sx={{ 
                  p: 3, 
                  borderRadius: 2, 
                  flex: 1,
                  backgroundColor: "white",
                  cursor: "pointer",
                  "&:hover": { boxShadow: 3 },
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
                onClick={() => setTabValue(1)}
              >
                <SmartToyIcon sx={{ fontSize: 40, color: "primary.main", mb: 2 }} />
                <Typography variant="h6" gutterBottom>Agents</Typography>
                <Typography variant="body2" align="center">
                  Browse and manage AI agents
                </Typography>
              </Paper>
              
              <Paper 
                elevation={1}
                sx={{ 
                  p: 3, 
                  borderRadius: 2, 
                  flex: 1,
                  backgroundColor: "white",
                  cursor: "pointer",
                  "&:hover": { boxShadow: 3 },
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
                onClick={() => setTabValue(2)}
              >
                <ChatIcon sx={{ fontSize: 40, color: "primary.main", mb: 2 }} />
                <Typography variant="h6" gutterBottom>Playground</Typography>
                <Typography variant="body2" align="center">
                  Interact with AI agents in the chat playground
                </Typography>
              </Paper>
            </Stack>
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <AgentComponent onAgentSelect={handleAgentSelect} />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <ChatPlayground preselectedAgentId={selectedAgentId} />
        </TabPanel>
      </Box>
    </Box>
  );
};

export default MainLayout;
