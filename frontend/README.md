# Agno Hub - Frontend

React TypeScript frontend for the Agno agent hub. Provides user interface for managing agents, viewing configurations, and interacting with agents through an intuitive chat playground.

## Frontend Architecture

```
frontend/
├── src/
│   ├── components/
│   │   ├── AgentComponent.tsx      # Agent cards display
│   │   ├── AgentDetailModal.tsx    # Agent details popup
│   │   ├── ChatPlayground.tsx      # Chat interface
│   │   ├── Header.tsx              # Navigation header
│   │   └── MainLayout.tsx          # Main layout wrapper
│   ├── services/
│   │   └── api.ts                  # HTTP client & endpoints
│   ├── theme/
│   │   └── theme.ts                # Color & styling theme
│   ├── App.tsx                     # Root component
│   ├── App.css                     # App styles
│   ├── index.tsx                   # Entry point
│   ├── index.css                   # Global styles
│   ├── App.test.tsx                # Tests
│   └── setupTests.ts               # Test configuration
├── public/
│   ├── index.html                  # HTML template
│   ├── manifest.json               # PWA manifest
│   └── robots.txt                  # SEO config
├── package.json                    # Dependencies
├── tsconfig.json                   # TypeScript config
└── README.md                       # This file
```

## Technology Stack

- **React** (18+) - UI library
- **TypeScript** - Type safety
- **CSS** - Component styling
- **Axios** - HTTP client for API calls
- **Node.js** 16+ - Runtime
- **npm** 8+ - Package manager

## Setup & Installation

### Prerequisites
```bash
Node.js 16+
npm 8+
Backend running on http://localhost:5000
```

### Installation

```bash
cd frontend
npm install
```

### Environment Configuration

Create `.env` file in `frontend/` directory:

```env
REACT_APP_API_URL=http://localhost:5000
```

## Development

### Start Development Server

```bash
npm start
```

Opens at: **http://localhost:3000**

The app will automatically reload on code changes.

### Build for Production

```bash
npm run build
```

Creates optimized production build in `build/` directory.

### Run Tests

```bash
npm test
```

## Components

### AgentComponent
**File:** `src/components/AgentComponent.tsx`

Core component that displays:
- Agent name and description
- Agent type badge (Simple/MCP)
- Active status indicator
- Agent ID reference

### AgentDetailModal
**File:** `src/components/AgentDetailModal.tsx`

Modal that shows:
- Complete agent configuration
- Model settings (model ID, max tokens)
- System instructions
- Tool configurations
- MCP settings (if MCP agent)

### ChatPlayground
**File:** `src/components/ChatPlayground.tsx`

Interactive interface with:
- Agent selection dropdown
- Message input field
- Conversation history display
- Real-time message streaming
- Error handling & display

### Header
**File:** `src/components/Header.tsx`

Navigation with:
- Hub title/branding
- Navigation links
- Active section indicator

### MainLayout
**File:** `src/components/MainLayout.tsx`

Page wrapper providing:
- Header inclusion
- Responsive layout
- Content area management

## API Client

**Location:** `src/services/api.ts`

### Exported Functions

```typescript
// Agent endpoints
getAllAgents()                          // GET /api/agents
getAgentById(id: string)                // GET /api/agents/{id}
getAgentByName(name: string)            // GET /api/agents/name/{name}
getActiveAgents()                       // GET /api/agents/active
getAgentsByType(type: string)           // GET /api/agents/type/{type}

// Host agent endpoints
getAllHostAgents()                      // GET /api/host-agents
getHostAgentById(id: string)            // GET /api/host-agents/{id}

// Execution endpoints
executeAgent(prompt: string, agentId: string) // POST /api/chat
```

### Usage Example

```typescript
import { getAllAgents, executeAgent } from '../services/api';

// Get all agents
const agents = await getAllAgents();

// Execute agent task
const response = await executeAgent('Tell me about AI', agent.agent_id);
```

## Theme

**Location:** `src/theme/theme.ts`

Configures:
- Color palette (primary, secondary, background)
- Typography settings
- Responsive breakpoints
- Component styling variables

## State Management

### Local State
Each component manages its own state:
- Agent list state
- Selected agent
- Chat messages
- Loading/error states

### API Communication
Uses Axios with error handling:
- Request interceptors for headers
- Response error handling
- Timeout configuration

## Styling

- **App.css** - Main application styles
- **index.css** - Global base styles
- **Component CSS** - Individual component styles
- **theme.ts** - Theme variables

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Troubleshooting

### API Connection Error

**Problem:** Can't connect to backend

**Solution:**
- Verify backend is running on `http://localhost:5000`
- Check `REACT_APP_API_URL` in `.env` file
- Check browser console for specific error
- Verify CORS is enabled in backend

### Module Not Found Error

**Problem:** `Module not found` error

**Solution:**
```bash
rm -rf node_modules package-lock.json
npm install
npm start
```

### Port 3000 Already in Use

**Problem:** Port 3000 is already in use

**Solution:**
```bash
# On Windows PowerShell:
Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess | Stop-Process

# On Linux/Mac:
lsof -i :3000 # Find process
kill -9 <PID> # Kill it

# Or use different port:
PORT=3001 npm start
```

### Build Fails

**Problem:** `npm run build` fails

**Solution:**
```bash
npm cache clean --force
rm -rf node_modules
npm install
npm run build
```

## Features

✓ **TypeScript** - Full type safety  
✓ **Responsive Design** - Mobile & desktop support  
✓ **Agent Management** - View all available agents  
✓ **Agent Details** - Inspect full agent configuration  
✓ **Chat Interface** - Interact with agents  
✓ **Error Handling** - User-friendly error messages  
✓ **Real-time Updates** - Instant message display  

## Performance Tips

1. **Lazy Load Components**
   ```typescript
   const ChatPlayground = React.lazy(() => import('./ChatPlayground'));
   ```

2. **Memoize Components**
   ```typescript
   export default React.memo(AgentComponent);
   ```

3. **Optimize Re-renders**
   - Use `useCallback` for event handlers
   - Use `useMemo` for expensive computations

## Development Workflow

1. Start backend on port 5000
2. Run `npm install` in frontend
3. Start frontend with `npm start`
4. Frontend opens at http://localhost:3000
5. Make changes - auto reload on save
6. Check console for errors/warnings
7. Build for production: `npm run build`

## Documentation Links

- [Main Hub README](../README.md) - Project overview
- [Backend README](../backend/README.md) - Backend setup & APIs
- [React Docs](https://react.dev)
- [TypeScript Docs](https://www.typescriptlang.org)
- [Axios Docs](https://axios-http.com)

## File Structure Guide

```
src/
├── App.tsx                    # Root component
├── App.css                    # App styles
├── index.tsx                  # ReactDOM entry
├── index.css                  # Global styles
├── components/                # React components folder
├── services/                  # API client & utilities
└── theme/                     # Theming configuration
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| REACT_APP_API_URL | http://localhost:5000 | Backend API endpoint |
| NODE_ENV | development | Environment (development/production) |

## Building & Deployment

### Development Build
```bash
npm start
```

### Production Build
```bash
npm run build
```

Built files go to `build/` directory.

### Deploy to Server

1. Build: `npm run build`
2. Copy `build/` contents to web server
3. Ensure API_URL points to backend
4. Serve with static file server

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| API 404 | Backend not running | Start backend on port 5000 |
| CORS error | Backend CORS not configured | Check backend CORS settings |
| Module not found | Dependencies not installed | Run `npm install` |
| Port in use | Port 3000 already used | Use `PORT=3001 npm start` |
| Blank page | Build issues | Clear cache, reinstall deps |

## Future Enhancements

- [ ] Agent creation UI
- [ ] Agent editing interface
- [ ] File upload support
- [ ] Chat history persistence
- [ ] Dark mode theme
- [ ] Multi-language support
- [ ] Accessibility improvements

## Support & Debugging

1. Check browser console (F12) for errors
2. Check network tab for API requests
3. Verify backend is running
4. Check .env file configuration
5. Review browser compatibility
6. Check firewall/proxy settings
