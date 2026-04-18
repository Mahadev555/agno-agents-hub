import React from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Box,
  Button,
  IconButton,
  useTheme,
  useMediaQuery
} from '@mui/material';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';
import GitHubIcon from '@mui/icons-material/GitHub';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

const Header: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  
  return (
    <AppBar 
      position="static" 
      elevation={2}
      sx={{
        background: 'linear-gradient(90deg, #3f51b5 0%, #5c6bc0 100%)',
      }}
    >
      <Toolbar>
        <Box display="flex" alignItems="center">
          <SmartToyOutlinedIcon sx={{ mr: 1, fontSize: 28 }} />
          <Typography
            variant="h5"
            component="div"
            sx={{ 
              fontWeight: 700,
              letterSpacing: '0.5px',
            }}
          >
            agno_hub Hub
          </Typography>
        </Box>
        
        <Box sx={{ flexGrow: 1 }} />
        
        {!isMobile && (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button 
              color="inherit" 
              startIcon={<HelpOutlineIcon />}
              sx={{ textTransform: 'none' }}
            >
              Documentation
            </Button>
            <IconButton 
              color="inherit" 
              size="small"
              sx={{ ml: 1 }}
            >
              <GitHubIcon />
            </IconButton>
          </Box>
        )}
      </Toolbar>
    </AppBar>
  );
};

export default Header;
