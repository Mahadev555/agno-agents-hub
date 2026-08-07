import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from controllers.agent_execution_controller import AgentExecutionController
from controllers.agents_controller import (
    AgentCreateRequest,
    AgentsController,
    AgentUpdateRequest,
    HostAgentCreateRequest,
    HostAgentsController,
)
from controllers.run_controller import RunController
from controllers.team_controller import (
    TeamCreateRequest,
    TeamsController,
    TeamUpdateRequest,
)
from services.run_bus import run_bus

logger = logging.getLogger(__name__)

# ======================= PYDANTIC MODELS =======================

class ChatMessage(BaseModel):
    message: str
    agentId: Optional[str | List[str]] = None

class AgentExecution(BaseModel):
    agentId: str
    parameters: Dict[str, Any]

# Single Agent Execution Request
class SingleAgentRequest(BaseModel):
    """Request to run a single agent"""
    prompt: str = Field(..., description="The task/prompt for the agent", min_length=1)
    agentId: int = Field(..., description="ID of the agent to run")

# Team/Workflow Execution Request
class TeamExecutionRequest(BaseModel):
    """Request to run a team with host agent coordination"""
    prompt: str = Field(..., description="The task/prompt for the team", min_length=1)
    hostAgentId: int = Field(..., description="ID of the host/coordinator agent")
    memberAgentIds: List[int] = Field(..., description="List of member agent IDs", min_length=1)

# Unified Chat Request (backward compatible)
class ChatRequest(BaseModel):
    """Chat request - supports both single and team modes"""
    prompt: str = Field(..., description="The prompt/task to execute", min_length=1)
    agentIds: Optional[List[int]] = Field(None, description="List of agent IDs to use")
    hostAgentId: Optional[int] = Field(None, description="Host agent ID for team mode")

# Execution Response (new standardized format)
class ExecutionResponse(BaseModel):
    """Response from agent/team execution"""
    response: str
    mode: str  # "single" or "team"
    agents_used: List[int]
    status: str  # "completed" or "error"
    execution_time: Optional[float] = None
    message: Optional[str] = None

# Chat Response (backward compatible for legacy /api/chat endpoint)
class ChatResponse(BaseModel):
    """Chat response with execution details (backward compatible)"""
    response: str
    agents: Optional[List[int]]
    status: str
    message: Optional[str] = None

router = APIRouter()


# ======================= AGENT CRUD ROUTES =======================
#
# Agent existence is checked by AgentExecutionController while it loads the
# configs it needs, so execution routes do not pre-validate. Doing both meant
# every request read each agent row twice.
#
# Literal paths must stay above /api/agents/{agent_id}; otherwise FastAPI
# matches the parameterized route first and /api/agents/mcp only works by
# accident of int coercion failing.

@router.get("/api/agents")
async def get_agents():
    """Get all agents"""
    return await AgentsController.get_all_agents()

@router.get("/api/agents/active")
async def get_active_agents():
    """Get all active agents"""
    return await AgentsController.get_active_agents()

@router.get("/api/agents/mcp")
async def get_mcp_agents():
    """Get all MCP agents"""
    return await AgentsController.get_agents_by_type("mcp")

@router.get("/api/agents/type/{agent_type}")
async def get_agents_by_type(agent_type: str):
    """Get agents by type (simple, mcp, host)"""
    return await AgentsController.get_agents_by_type(agent_type)

@router.get("/api/agents/name/{name}")
async def get_agent_by_name(name: str):
    """Get agent by name"""
    return await AgentsController.get_agent_by_name(name)

@router.get("/api/agents/{agent_id}")
async def get_agent_by_id(agent_id: int):
    """Get a specific agent by ID"""
    return await AgentsController.get_agent_by_id(agent_id)

# Create endpoint
@router.post("/api/agents")
async def create_agent(agent_data: AgentCreateRequest):
    """Create a new agent"""
    return await AgentsController.create_agent(agent_data)

# Update endpoint
@router.put("/api/agents/{agent_id}")
async def update_agent(agent_id: int, agent_data: AgentUpdateRequest):
    """Update an existing agent"""
    return await AgentsController.update_agent(agent_id, agent_data)

# Delete endpoint
@router.delete("/api/agents/{agent_id}")
async def delete_agent(agent_id: int):
    """Delete an agent"""
    return await AgentsController.delete_agent(agent_id)


# ======================= HOST AGENT ROUTES =======================

@router.get("/api/host-agents")
async def get_host_agents():
    """Get all host agents"""
    return await HostAgentsController.get_all_host_agents()

@router.get("/api/host-agents/{agent_id}")
async def get_host_agent_by_id(agent_id: int):
    """Get a specific host agent by ID"""
    return await HostAgentsController.get_host_agent_by_id(agent_id)

@router.post("/api/host-agents")
async def create_host_agent(agent_data: HostAgentCreateRequest):
    """Create a new host agent"""
    return await HostAgentsController.create_host_agent(agent_data)


# ======================= AGENT EXECUTION ROUTES =======================

@router.post("/api/chat", response_model=ChatResponse)
async def process_chat(chat_request: ChatRequest):
    """
    Process a chat message using agents.
    
    This endpoint:
    1. Validates the prompt
    2. Validates and loads agent IDs if provided
    3. Dynamically creates agents from database configs
    4. Executes the task with selected agents
    
    Request body:
    {
        "prompt": "Your task/question here",
        "agentIds": [1, 2]  // optional - specific agents to use
    }
    
    Response:
    {
        "response": "Generated response",
        "agents": [1, 2],
        "status": "completed|error",
        "message": "Optional message"
    }
    """
    try:
        logger.info(f"📬 Received chat request")
        logger.info(f"   Prompt: {chat_request.prompt[:100]}...")
        logger.info(f"   Agent IDs: {chat_request.agentIds}")
        
        # Step 1: Validate prompt
        if not chat_request.prompt or not chat_request.prompt.strip():
            logger.warning("❌ Empty prompt received")
            raise HTTPException(
                status_code=400, 
                detail="Prompt cannot be empty. Please provide a valid task or question."
            )
        
        # Step 2: Execute agent task. The controller loads and validates the
        # agents as part of setting up the run.
        logger.info("Executing agent task...")
        result = await AgentExecutionController.execute_agent_task(
            prompt=chat_request.prompt.strip(),
            agent_ids=chat_request.agentIds,
            host_agent_id=chat_request.hostAgentId,
        )
        
        # Step 4: Process and return response
        if result.get("status") == "completed":
            logger.info("✅ Task completed successfully")
            return ChatResponse(
                response=result.get("content") or "No response generated",
                agents=chat_request.agentIds,
                status="completed",
                message="Task executed successfully"
            )
        else:
            error_msg = result.get("message", "Unknown error")
            logger.error(f"❌ Task failed: {error_msg}")
            return ChatResponse(
                response=result.get("content") or "",
                agents=chat_request.agentIds,
                status="error",
                message=error_msg
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error processing chat: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Unexpected error: {str(e)}"
        )


# ======================= SINGLE AGENT EXECUTION =======================

@router.post("/api/agent/run", response_model=ExecutionResponse)
async def run_single_agent(request: SingleAgentRequest):
    """
    Execute a single agent directly.
    
    Request:
    {
        "prompt": "Your task here",
        "agentId": 3
    }
    
    Response:
    {
        "response": "Generated response",
        "mode": "single",
        "agents_used": [3],
        "status": "completed",
        "execution_time": 2.5
    }
    """
    try:
        import time
        start_time = time.time()
        
        logger.info(f"Single agent execution | agent_id={request.agentId} | "
                    f"prompt={request.prompt[:100]}")

        result = await AgentExecutionController.execute_single_agent(
            prompt=request.prompt.strip(),
            agent_id=request.agentId
        )
        
        execution_time = time.time() - start_time
        logger.info(f"⏱️  Execution time: {execution_time:.2f}s")
        
        # Step 3: Return response
        if result.get("status") == "completed":
            logger.info("✅ Single agent execution successful")
            return ExecutionResponse(
                response=result.get("content") or "No response generated",
                mode="single",
                agents_used=[request.agentId],
                status="completed",
                execution_time=execution_time,
                message="Agent executed successfully"
            )
        else:
            logger.error(f"❌ Execution failed: {result.get('message')}")
            return ExecutionResponse(
                response=result.get("content") or "",
                mode="single",
                agents_used=[request.agentId],
                status="error",
                execution_time=execution_time,
                message=result.get("message")
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in single agent execution: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ======================= TEAM EXECUTION =======================

@router.post("/api/team/run", response_model=ExecutionResponse)
async def run_team(request: TeamExecutionRequest):
    """
    Execute a team with host agent coordination.
    
    The host agent acts as a coordinator that divides tasks among member agents
    and consolidates results.
    
    Request:
    {
        "prompt": "Your task here",
        "hostAgentId": 1,
        "memberAgentIds": [2, 3, 4]
    }
    
    Response:
    {
        "response": "Consolidated response from host agent",
        "mode": "team",
        "agents_used": [1, 2, 3, 4],
        "status": "completed",
        "execution_time": 5.5
    }
    """
    try:
        import time
        start_time = time.time()
        
        logger.info(f"Team execution | host={request.hostAgentId} | "
                    f"members={request.memberAgentIds} | prompt={request.prompt[:100]}")

        result = await AgentExecutionController.execute_team(
            prompt=request.prompt.strip(),
            host_agent_id=request.hostAgentId,
            member_agent_ids=request.memberAgentIds
        )
        
        execution_time = time.time() - start_time
        logger.info(f"⏱️  Execution time: {execution_time:.2f}s")
        
        # Step 4: Return response
        all_agents = [request.hostAgentId] + request.memberAgentIds
        if result.get("status") == "completed":
            logger.info("✅ Team execution successful")
            return ExecutionResponse(
                response=result.get("content") or "No response generated",
                mode="team",
                agents_used=all_agents,
                status="completed",
                execution_time=execution_time,
                message="Team executed successfully with host coordination"
            )
        else:
            logger.error(f"❌ Team execution failed: {result.get('message')}")
            return ExecutionResponse(
                response=result.get("content") or "",
                mode="team",
                agents_used=all_agents,
                status="error",
                execution_time=execution_time,
                message=result.get("message")
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in team execution: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")



# ======================= RUN ROUTES (streaming) =======================

class TeamRunRequest(BaseModel):
    """Run a saved team."""
    prompt: str = Field(..., description="The task to execute", min_length=1)


class RunCreateRequest(BaseModel):
    """Start a run. One agent runs alone; several are coordinated by a host."""
    prompt: str = Field(..., description="The task to execute", min_length=1)
    agentIds: Optional[List[int]] = Field(None, description="Agent IDs to use")
    hostAgentId: Optional[int] = Field(None, description="Coordinator for team mode")
    teamId: Optional[int] = Field(None, description="Run a saved team by id")


@router.post("/api/runs", status_code=202)
async def create_run(request: RunCreateRequest):
    """
    Start a run and return immediately with its id.

    Execution continues server-side regardless of what the client does next, so
    a closed tab or a proxy timeout no longer discards the work. Subscribe to
    /api/runs/{run_id}/events for progress, or poll /api/runs/{run_id}.
    """
    return RunController.start(
        prompt=request.prompt,
        agent_ids=request.agentIds,
        host_agent_id=request.hostAgentId,
        team_id=request.teamId,
    )


@router.get("/api/runs")
async def list_runs(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by run status"),
):
    """List recent runs, newest first."""
    return RunController.list_recent(limit=limit, status=status)


@router.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    """Fetch a single run record."""
    return RunController.get(run_id)


@router.get("/api/runs/{run_id}/events")
async def stream_run_events(run_id: str, request: Request):
    """
    Server-sent events for a run.

    Replays everything already emitted before streaming live output, so a
    client that subscribes slightly late still sees the whole run. If the run
    has already finished, its terminal state is replayed from the database and
    the stream closes immediately.
    """
    record = RunController.get(run_id)  # 404s for unknown ids

    async def event_source():
        channel = run_bus.get(run_id)

        if channel is None:
            # Not in flight: reconstruct a terminal event from the stored row.
            if record["status"] == "completed":
                payload = {"type": "completed", "output": record.get("output") or "",
                           "usage": {"total_tokens": record.get("total_tokens")}}
            elif record["status"] == "error":
                payload = {"type": "error", "message": record.get("error") or "Run failed"}
            else:
                payload = {"type": "error",
                           "message": "Run is not active on this server and has no result"}
            yield _sse(payload)
            return

        try:
            async for event in channel.subscribe():
                yield _sse(event)
        except asyncio.CancelledError:
            # Raised into the generator when the client goes away; the finally
            # block below still runs. An explicit is_disconnected() poll here
            # would additionally drop the event already taken off the queue.
            raise
        finally:
            # Drop the channel once it is closed and nobody is reading it.
            if channel.closed:
                run_bus.discard(run_id)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Stops nginx buffering the stream into uselessness.
            "X-Accel-Buffering": "no",
        },
    )


def _sse(payload: Dict[str, Any]) -> str:
    """Encode one event in the SSE wire format."""
    return f"data: {json.dumps(payload)}\n\n"


# ======================= TEAM ROUTES =======================
#
# Teams persist composition, so a group of agents can be named, reused, and
# shared instead of being re-specified by the client on every request.

@router.get("/api/teams")
async def list_teams():
    """List all teams with their members."""
    return await TeamsController.list_teams()


@router.post("/api/teams", status_code=201)
async def create_team(payload: TeamCreateRequest):
    """Create a reusable team."""
    return await TeamsController.create_team(payload)


@router.get("/api/teams/{team_id}")
async def get_team(team_id: int):
    """Fetch a team by id."""
    return await TeamsController.get_team(team_id)


@router.put("/api/teams/{team_id}")
async def update_team(team_id: int, payload: TeamUpdateRequest):
    """Update a team. Supplying memberAgentIds replaces membership entirely."""
    return await TeamsController.update_team(team_id, payload)


@router.delete("/api/teams/{team_id}")
async def delete_team(team_id: int):
    """Delete a team. Membership rows cascade; the agents themselves remain."""
    return await TeamsController.delete_team(team_id)


@router.post("/api/teams/{team_id}/runs", status_code=202)
async def run_team(team_id: int, request: TeamRunRequest):
    """Start a run using a saved team's coordinator and membership."""
    return RunController.start(prompt=request.prompt, team_id=team_id)
