# Agno Agents Hub

A comprehensive AI agent orchestration platform built with FastAPI, React, and the **Agno Framework**. Create, manage, and coordinate multiple AI agents for complex tasks.

## About Agno Framework

[Agno](https://github.com/agno-agi/agno) is a powerful framework for building agent-based systems. It provides:

### Core Capabilities
- **Dynamic Agent Creation** - Build agents programmatically from configurations
- **Team Orchestration** - Coordinate multiple agents to work together
- **Tool Integration** - Connect agents to external tools and APIs
- **MCP Support** - Model Context Protocol for advanced capabilities
- **LLM Integration** - Works with Azure OpenAI, OpenAI, and other providers
- **Flexible Execution** - Run agents in sequential, parallel, or coordinated modes
- **Memory Management** - Persistent conversation history and state management
- **Error Handling** - Built-in retry logic and fallback mechanisms

### Why Agno?
- **Production-Ready** - Battle-tested framework used in enterprise systems
- **Composable** - Build complex multi-agent systems from simple components
- **Type-Safe** - Full Python type hints for better IDE support
- **Extensible** - Easy to add custom agents, tools, and integrations
- **Multi-LLM Support** - Switch between different LLM providers seamlessly
- **Fast & Efficient** - Optimized for low-latency agent interactions

This project uses Agno to create a flexible hub where agents can be dynamically instantiated, managed, and coordinated efficiently.

## Project Overview

Agno Hub is a multi-agent system that allows you to:
- **Define Agents** - Create agent configurations in JSON
- **Store Agents** - Save agent definitions in PostgreSQL database
- **Manage Agents** - Full CRUD APIs for agent lifecycle management
- **Execute Agents** - Run agents individually or in coordinated teams
- **Interact** - Chat interface to communicate with agents

## Project Structure

```
Agno-Hub/
├── backend/                         # FastAPI application
│   ├── models/                      # SQLAlchemy ORM models
│   │   ├── agent.py                 # Agent & HostAgent models
│   │   └── agents_model.py          # Config retrieval functions
│   ├── services/                    # Business logic
│   │   ├── database_service.py      # Database operations
│   │   └── agent_service.py         # Agent CRUD logic
│   ├── controllers/                 # API request handlers
│   │   ├── agents_controller.py     # Agent endpoints
│   │   └── agent_execution_controller.py  # Execution logic
│   ├── routes/
│   │   └── routes.py                # API endpoint definitions
│   ├── agents/
│   │   ├── configs/                 # JSON agent configurations
│   │   │   ├── simple_agents/       # SimpleAgent configs
│   │   │   ├── mcp_agents/          # MCPAgent configs
│   │   │   └── host_config.json     # HostAgent (orchestrator) config
│   │   ├── hosts/
│   │   │   └── host_agent.py        # Dynamic team creation (uses Agno)
│   │   └── subhost/
│   │       └── agent.py             # Agent execution orchestration
│   ├── connection.py                # SQLAlchemy setup
│   ├── app.py                       # FastAPI application
│   ├── run_server.py                # Server startup
│   ├── seed_database.py             # Database seeder
│   ├── requirements.txt             # Python dependencies
│   ├── README.md                    # Backend documentation
│   └── ARCHITECTURE.md              # Detailed architecture
│
├── frontend/                        # React TypeScript application
│   ├── src/
│   │   ├── components/              # React components
│   │   ├── services/                # API client
│   │   ├── theme/                   # UI theming
│   │   └── App.tsx                  # Root component
│   ├── public/                      # Static assets
│   ├── package.json                 # Node dependencies
│   ├── tsconfig.json                # TypeScript config
│   └── README.md                    # Frontend documentation
│
└── README.md                        # This file
```

## Technology Stack

### Backend
- **FastAPI** (0.115.13) - Modern web framework
- **SQLAlchemy** (2.0.41) - ORM for database
- **PostgreSQL** - Database (via Neon Cloud)
- **Pydantic v2** - Data validation
- **Agno** (1.5.10) - Agent orchestration framework
- **Azure OpenAI** - LLM backend
- **Python** 3.12+

### Frontend
- **React** 18+ - UI library
- **TypeScript** - Type safety
- **CSS** - Styling
- **Axios** - HTTP client
- **Node.js** 16+

### Database
- **PostgreSQL** - Relational database
- **Neon Cloud** - Managed PostgreSQL hosting

## Getting Started

### Quick Start

1. **Clone Repository**
   ```bash
   cd Agno-Hub
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv .venv
   # On Windows:
   .\.venv\Scripts\activate
   # On Linux/Mac:
   source .venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   Create `backend/.env`:
   ```env
   DATABASE_URL="postgresql://user:password@host:port/database"
   AZURE_OPENAI_API_KEY='your_key'
   AZURE_OPENAI_ENDPOINT='your_endpoint'
   AZURE_OPENAI_DEPLOYMENT='deployment_name'
   AZURE_OPENAI_API_VERSION='2025-01-01-preview'
   ```

4. **Initialize Database**
   ```bash
   python seed_database.py
   ```

5. **Start Backend**
   ```bash
   python run_server.py
   ```
   Backend: http://localhost:5000

6. **Frontend Setup** (in new terminal)
   ```bash
   cd frontend
   npm install
   npm start
   ```
   Frontend: http://localhost:3000

## Key Features

✓ **Dynamic Agents** - Create agents from JSON configurations  
✓ **SQLAlchemy ORM** - Type-safe database operations  
✓ **CRUD APIs** - Full agent lifecycle management  
✓ **Agno Framework** - Powerful agent orchestration  
✓ **Multiple Agent Types** - Simple, MCP, and Host agents  
✓ **Chat Interface** - Interact with agents  
✓ **REST APIs** - Comprehensive API documentation  
✓ **TypeScript Frontend** - Type-safe React application  
✓ **Database Seeding** - Easy sample data population  

## Agent Types

### SimpleAgent
Basic agent with:
- LLM model configuration
- System instructions
- Tool access
- No MCP required

### MCPAgent
Advanced agent with:
- Model Context Protocol support
- MCP server integration
- Extended capabilities
- MCP configuration

### HostAgent
Orchestrator that:
- Coordinates multiple agents
- Creates dynamic teams
- Runs in coordinate/sequential/parallel modes
- Uses Agno Team framework

## API Documentation

**Full API Docs:** http://localhost:5000/docs (Swagger UI)  
**Alternative:** http://localhost:5000/redoc (ReDoc)

## Detailed Documentation

- [Backend README](./backend/README.md) - Backend API & architecture
- [Frontend README](./frontend/README.md) - Frontend setup & components

## Resources

- [Agno GitHub](https://github.com/agno-agi/agno)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [React Docs](https://react.dev)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org)
- [PostgreSQL Docs](https://www.postgresql.org/docs)

---

Made with 🧠 ❤️ by **Mahadev Manerikar**
