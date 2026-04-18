# Agno Hub - Backend API

FastAPI-based backend for the Agno agent hub. Provides REST APIs for agent management, orchestration, and execution using SQLAlchemy ORM with PostgreSQL.

## Backend Architecture

```
backend/
├── models/
│   ├── agent.py                    # SQLAlchemy models (Agent, HostAgent)
│   └── agents_model.py             # Agent config retrieval functions
│
├── services/
│   ├── database_service.py         # All database operations (ORM)
│   └── agent_service.py            # Agent CRUD & business logic
│
├── controllers/
│   ├── agents_controller.py        # API request handlers + Pydantic models
│   └── agent_execution_controller.py   # Task execution logic
│
├── routes/
│   └── routes.py                   # API endpoints
│
├── agents/
│   ├── configs/                    # JSON agent configurations
│   │   ├── simple_agents/          # SimpleAgent configs
│   │   ├── mcp_agents/             # MCPAgent configs
│   │   └── host_config.json        # HostAgent (orchestrator) config
│   ├── hosts/
│   │   └── host_agent.py           # Dynamic team creation with Agno
│   └── subhost/
│       └── agent.py                # Agent execution orchestration
│
├── connection.py                   # SQLAlchemy setup
├── app.py                          # FastAPI application
├── run_server.py                   # Server startup
├── seed_database.py                # Database seeder
├── requirements.txt                # Python dependencies
└── ARCHITECTURE.md                 # Detailed architecture
```

## Core Technologies

- **FastAPI** (0.115.13) - Web framework
- **SQLAlchemy** (2.0.41) - ORM
- **PostgreSQL + Neon** - Database
- **Pydantic v2** (2.11.5) - Data validation
- **Agno** (1.5.10) - Agent orchestration framework
- **Azure OpenAI** - LLM backend
- **MCPTools** - Model Context Protocol support

## Setup

### Prerequisites
- Python 3.12+
- PostgreSQL or Neon Cloud account
- Azure OpenAI API credentials

### Installation

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment:**
   Create `.env` file:
   ```env
   DATABASE_URL="postgresql://user:password@host:port/database"
   AZURE_OPENAI_API_KEY='your_key'
   AZURE_OPENAI_ENDPOINT='your_endpoint'
   AZURE_OPENAI_DEPLOYMENT='deployment_name'
   AZURE_OPENAI_API_VERSION='2025-01-01-preview'
   ```

3. **Initialize Database:**
   ```bash
   python seed_database.py
   ```
   This creates tables and populates with sample agents from `agents/configs/`

## Running the Backend

### Development Server
```bash
python run_server.py
```

Server runs at: `http://localhost:5000`

**API Documentation:**
- Swagger UI: `http://localhost:5000/docs`
- ReDoc: `http://localhost:5000/redoc`

### Production Server
```bash
python -m uvicorn app:app --host 0.0.0.0 --port 5000 --workers 4
```

## API Endpoints

### Agent Management

**Get Endpoints:**
- `GET /api/agents` - List all agents
- `GET /api/agents/active` - List active agents only
- `GET /api/agents/type/{agent_type}` - Filter by type (simple, mcp)
- `GET /api/agents/name/{name}` - Get agent by name
- `GET /api/agents/{id}` - Get agent by ID

**Create/Update:**
- `POST /api/agents` - Create new agent
- `PUT /api/agents/{id}` - Update agent
- `DELETE /api/agents/{id}` - Delete agent

### Host Agent Management

- `GET /api/host-agents` - List all host agents
- `GET /api/host-agents/{id}` - Get host agent by ID
- `POST /api/host-agents` - Create host agent

### Execution

- `POST /api/chat` - Execute agent task with prompt

## Database Schema

### agents table
```sql
agent_id (PK)          # Auto-increment
name (UNIQUE)          # Agent name
description            # Text description
agent_type             # Type: simple, mcp
is_mcp                 # Boolean flag
is_active              # Boolean flag
mcp_config (JSONB)     # MCP configuration
config (JSONB)         # Full agent configuration
created_at             # Timestamp
updated_at             # Timestamp
```

### host_agent table
```sql
agent_id (PK)          # Auto-increment
name (UNIQUE)          # Host agent name
description            # Text description
is_mcp                 # Boolean flag
is_active              # Boolean flag
mode                   # coordinate|sequential|parallel
config (JSONB)         # Orchestration configuration
created_at             # Timestamp
updated_at             # Timestamp
```

## Agent Configuration Formats

### Simple Agent Config
File: `agents/configs/simple_agents/agent_name.json`

```json
{
  "name": "Research Agent",
  "description": "Researches topics",
  "is_mcp": false,
  "config": {
    "name": "Research Agent",
    "role": "Researcher",
    "model_config": {
      "type": "azure",
      "id": "gpt-4o",
      "max_tokens": 4096
    },
    "instructions": ["Research thoroughly"],
    "tools": [],
    "markdown": true,
    "show_tool_calls": true
  }
}
```

### MCP Agent Config
File: `agents/configs/mcp_agents/agent_name.json`

```json
{
  "name": "MCP Agent",
  "description": "Uses Model Context Protocol",
  "is_mcp": true,
  "mcp_config": {
    "url": "http://localhost:3001/sse",
    "transport": "sse",
    "timeout_seconds": 300
  },
  "config": {
    "name": "MCP Agent",
    "role": "Specialist",
    "model_config": {
      "type": "azure",
      "id": "gpt-4o",
      "max_tokens": 8192
    },
    "instructions": ["Use MCP tools"],
    "tools": [],
    "markdown": true,
    "show_tool_calls": true
  }
}
```

### Host Agent Config
File: `agents/configs/host_config.json`

```json
{
  "name": "Mixed Agent Team",
  "description": "Coordinates multiple agents",
  "mode": "coordinate",
  "config": {
    "name": "Mixed Agent Team",
    "mode": "coordinate",
    "model_config": {
      "type": "azure",
      "id": "gpt-4o",
      "max_tokens": 16384
    },
    "instructions": ["Coordinate between agents"],
    "additional_params": {
      "show_tool_calls": true,
      "markdown": true
    }
  }
}
```

## Layer Architecture

```
Client Request
    ↓
Routes (routes.py)
    ↓
Controllers (agents_controller.py)
    ↓
Services (agent_service.py, database_service.py)
    ↓
Models (SQLAlchemy ORM)
    ↓
Database (PostgreSQL)
```

## Key Features

✓ **SQLAlchemy ORM** - Type-safe database operations
✓ **Automatic Table Creation** - Tables created on startup
✓ **CRUD APIs** - Full agent management
✓ **Dynamic Agents** - Create agents from JSON configs
✓ **Multiple Agent Types** - Simple, MCP, Host agents
✓ **Pydantic Validation** - Request/response validation
✓ **Agno Integration** - Dynamic team orchestration
✓ **Async Support** - FastAPI async endpoints

## Troubleshooting

### Database Connection Error
- Check `DATABASE_URL` in `.env`
- Verify PostgreSQL/Neon host is reachable
- Confirm credentials are correct

### Agent Not Loading
- Check JSON config format in `agents/configs/`
- Run `python seed_database.py` to reseed
- Verify `name` field matches across config

### API Not Responding
- Check port 5000 is not in use
- Verify FastAPI is running: `python run_server.py`
- Check logs for errors

### Azure OpenAI Issues
- Verify credentials in `.env`
- Confirm endpoint format: `https://<resource>.openai.azure.com/`
- Check API version compatibility

## Adding New Agents

1. **Create Config File:**
   - Simple: `agents/configs/simple_agents/my_agent.json`
   - MCP: `agents/configs/mcp_agents/my_agent.json`

2. **Populate Database:**
   ```bash
   python seed_database.py
   ```

3. **Verify via API:**
   ```bash
   curl http://localhost:5000/api/agents
   ```

## Services Overview

### DatabaseService
Handles all database operations using SQLAlchemy ORM:
- `get_all_agents()` - Retrieve all agents
- `get_agent_by_id(id)` - Get specific agent
- `get_agent_by_name(name)` - Get agent by name
- `get_active_agents()` - Get active agents only
- `get_agents_by_type(type)` - Filter by type
- `get_all_host_agents()` - Get orchestrators
- `get_host_agent_by_name(name)` - Get host by name

### AgentService
Business logic for agent management:
- `create_agent()` - Create new agent
- `update_agent()` - Update existing agent
- `delete_agent()` - Delete agent

### HostAgentService
Orchestrator agent management:
- `create_host_agent()` - Create orchestrator
- (Query operations delegated to DatabaseService)

## API Example Usage

### Create Agent
```bash
curl -X POST http://localhost:5000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Agent",
    "description": "Test agent",
    "agent_type": "simple",
    "is_mcp": false,
    "config": {...}
  }'
```

### Get All Agents
```bash
curl http://localhost:5000/api/agents
```

### Execute Chat
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is Python?"}'
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URI | postgresql://user:pass@host/db |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | your-api-key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | https://resource.openai.azure.com/ |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name | gpt-4o |
| `AZURE_OPENAI_API_VERSION` | API version | 2025-01-01-preview |

## Performance Notes

- Database connections use connection pooling (NullPool)
- Automatic connection cleanup on errors
- JSONB columns for flexible config storage
- All queries use SQLAlchemy for SQL injection protection

## Next Steps

1. [Main README](../README.md) - Project overview
2. [Frontend README](../frontend/README.md) - Frontend setup
3. [ARCHITECTURE.md](./ARCHITECTURE.md) - Detailed architecture
