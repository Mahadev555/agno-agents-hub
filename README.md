# Agno Hub

This project implements a multi-agent system.

## Project Structure

- `agents/` - Contains all agent-related code and configurations
  - `hosts/` - Supervisor agents for different functionalities
  - `subhost/` - Individual agent implementations and configurations
- `controllers/` - API controllers for the application
- `client/` - React frontend application
- `mcp_servers/` - Model Context Protocol servers
- `models/` - Data models and schemas
- `routes/` - API route definitions

## Setup Instructions

Follow these steps to set up and run the project:

### 1. Frontend Setup

First, build the frontend React application:

```bash
cd client
npm install
npm run build
```

This will create a production build that will be served by the FastAPI backend.

### 2. Backend Setup

Go back to the root directory and create a Python virtual environment:

```bash
cd ..
python -m venv venv
```

Activate the virtual environment:

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

Install required Python packages:

```bash
pip install -r requirements.txt
```

### 3. Database Setup

Start a PostgreSQL container with Docker:

```bash
docker run --name agno_hub-postgres -e POSTGRES_USER=agno_hub -e POSTGRES_PASSWORD=agno_hub -e POSTGRES_DB=agno_hub -p 6001:5432 -d postgres
```

Create the required database tables by running the following SQL script:

```sql
-- public.agents definition
CREATE TABLE public.agents (
    agent_id serial4 NOT NULL,
    "name" text NOT NULL,
    description text NULL,
    is_mcp bool DEFAULT false NULL,
    config jsonb NOT NULL,
    CONSTRAINT agents_pkey PRIMARY KEY (agent_id)
);

-- public.host_agent definition
CREATE TABLE public.host_agent (
    agent_id serial4 NOT NULL,
    "name" text NOT NULL,
    description text NULL,
    is_mcp bool DEFAULT false NULL,
    config jsonb NOT NULL,
    CONSTRAINT host_agent_pkey PRIMARY KEY (agent_id)
);
```

You can run this script using a PostgreSQL client such as psql or pgAdmin, or save it as a file (e.g., `setup.sql`) and run:

### 4. Environment Configuration

Create a `.env` file in the root directory with the following content:

```
DATABASE_URL="postgresql://agno_hub:agno_hub@localhost:6001/agno_hub"

AZURE_OPENAI_API_KEY='your_azure_openai_api_key'
AZURE_OPENAI_ENDPOINT='your_azure_openai_endpoint'
AZURE_OPENAI_DEPLOYMENT='chat4'
AZURE_OPENAI_API_VERSION='2025-01-01-preview'

```

Make sure to replace the placeholder values with your actual API keys and credentials.

### 5. Running the Application

After completing all the setup steps, start the application:

```bash
python -m uvicorn app:app --host localhost --port 5000 --reload
```

The application will be available at:
- Web UI: http://localhost:5000
- API: http://localhost:5000/api

## Features

- Browse and manage AI agents
- Interact with agents through a chat interface
- Detailed agent information and configuration
- Real-time chat responses

## Troubleshooting

### Database Connection Issues

If you encounter database connection issues, verify:
- The PostgreSQL container is running: `docker ps`
- The connection string in `.env` matches your container setup
- The database and tables have been created correctly

### API Key Issues

If AI agents aren't responding correctly, check:
- Your Azure OpenAI API keys are correctly set in the `.env` file
- The service endpoints are accessible from your environment

1. Start the MCP Server:
```powershell
cd mcp_servers/engagement_mcp_server
python -m mcp_fastapi
```

2. Run the Agent (from project root):
```powershell
python -m agents.subhost.agent
```

## Adding New Agents

### Team Agents
To add new agents to the team, append agent configurations to `agents/subhost/subhost_config.json`.

### Host Agents
To add new host agents, update the configuration in `agents/subhost/host_agent_config.json`.