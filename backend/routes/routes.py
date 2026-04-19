from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from controllers.agents_controller import (
    AgentsController,
    HostAgentsController,
    AgentCreateRequest,
    AgentUpdateRequest,
    HostAgentCreateRequest,
)
from controllers.agent_execution_controller import AgentExecutionController
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
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
    memberAgentIds: List[int] = Field(..., description="List of member agent IDs", min_items=1)

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


# ======================= HELPER FUNCTIONS =======================

async def validate_agent_exists(agent_id: int, is_host: bool = False) -> Dict[str, Any]:
    """Validate that an agent exists in the database."""
    from services.database_service import DatabaseService
    
    if is_host:
        agent = DatabaseService.get_host_agent_by_id(agent_id)
        agent_type = "Host Agent"
    else:
        agent = DatabaseService.get_agent_by_id(agent_id)
        agent_type = "Agent"
    
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"{agent_type} with ID {agent_id} not found in database"
        )
    
    logger.info(f"✅ Validated {agent_type} ID {agent_id}: {agent.get('name', 'Unknown')}")
    return agent

async def validate_and_load_agents(agent_ids: Optional[List[int]]) -> Dict[str, Any]:
    """
    Validate agent IDs and load their configurations from database.
    
    Args:
        agent_ids: List of agent IDs to validate and load
        
    Returns:
        Dict with validation status and loaded agent configs
        
    Raises:
        HTTPException: If validation fails
    """
    if not agent_ids:
        logger.info("No specific agent IDs provided, will use all available agents")
        return {"valid": True, "agent_ids": None, "agents": []}
    
    from services.database_service import DatabaseService
    
    if not isinstance(agent_ids, list):
        raise HTTPException(status_code=400, detail="agentIds must be a list of integers")
    
    loaded_agents = []
    invalid_ids = []
    
    for agent_id in agent_ids:
        if not isinstance(agent_id, int):
            raise HTTPException(status_code=400, detail=f"Agent ID must be integer, got {type(agent_id)}")
        
        try:
            agent = DatabaseService.get_agent_by_id(agent_id)
            if agent:
                loaded_agents.append(agent)
                logger.info(f"✅ Loaded agent ID {agent_id}: {agent.get('name', 'Unknown')}")
            else:
                invalid_ids.append(agent_id)
                logger.warning(f"⚠️ Agent ID {agent_id} not found in database")
        except Exception as e:
            logger.error(f"Error loading agent {agent_id}: {e}")
            invalid_ids.append(agent_id)
    
    if invalid_ids:
        raise HTTPException(
            status_code=404, 
            detail=f"Agent IDs not found: {invalid_ids}. Please check agent IDs and try again."
        )
    
    return {
        "valid": True,
        "agent_ids": agent_ids,
        "agents": loaded_agents
    }


# ======================= AGENT CRUD ROUTES =======================

# Get endpoints
@router.get("/api/agents")
async def get_agents():
    """Get all agents"""
    return await AgentsController.get_all_agents()

@router.get("/api/agents/active")
async def get_active_agents():
    """Get all active agents"""
    return await AgentsController.get_active_agents()

@router.get("/api/agents/type/{agent_type}")
async def get_agents_by_type(agent_type: str):
    """Get agents by type (simple, mcp, host)"""
    return await AgentsController.get_agents_by_type(agent_type)

@router.get("/api/agents/mcp")
async def get_mcp_agents():
    """Get all MCP agents"""
    return await AgentsController.get_agents_by_type("mcp")

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
        
        # Step 2: Validate and load agents if IDs provided
        agent_validation = await validate_and_load_agents(chat_request.agentIds)
        
        if not agent_validation["valid"]:
            logger.error("❌ Agent validation failed")
            raise HTTPException(status_code=400, detail="Agent validation failed")
        
        agents_loaded = agent_validation.get("agents", [])
        if chat_request.agentIds:
            logger.info(f"✅ Validated {len(agents_loaded)} agents successfully")
            for agent in agents_loaded:
                logger.info(f"   - {agent.get('name', 'Unknown')} (ID: {agent.get('agent_id')})")
        
        # Step 3: Execute agent task
        logger.info("🚀 Executing agent task...")
        result = await AgentExecutionController.execute_agent_task(
            prompt=chat_request.prompt.strip(),
            agent_ids=chat_request.agentIds
        )
        
        # Step 4: Process and return response
        if result.get("status") == "completed":
            logger.info("✅ Task completed successfully")
            return ChatResponse(
                response=result.get("content", "No response generated"),
                agents=chat_request.agentIds,
                status="completed",
                message="Task executed successfully"
            )
        else:
            error_msg = result.get("message", "Unknown error")
            logger.error(f"❌ Task failed: {error_msg}")
            return ChatResponse(
                response=result.get("content", ""),
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
        
        logger.info("=" * 80)
        logger.info("🎯 SINGLE AGENT EXECUTION")
        logger.info("=" * 80)
        logger.info(f"📋 Agent ID: {request.agentId}")
        logger.info(f"📝 Prompt: {request.prompt[:100]}...")
        
        # Step 1: Validate agent exists
        agent = await validate_agent_exists(request.agentId, is_host=False)
        logger.info(f"✅ Agent validated: {agent.get('name', 'Unknown')}")
        
        # Step 2: Execute single agent
        logger.info("🚀 Executing agent...")
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
                response=result.get("content", "No response generated"),
                mode="single",
                agents_used=[request.agentId],
                status="completed",
                execution_time=execution_time,
                message="Agent executed successfully"
            )
        else:
            logger.error(f"❌ Execution failed: {result.get('message')}")
            return ExecutionResponse(
                response=result.get("content", ""),
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
        
        logger.info("=" * 80)
        logger.info("👥 TEAM EXECUTION WITH HOST COORDINATION")
        logger.info("=" * 80)
        logger.info(f"🎯 Host Agent ID: {request.hostAgentId}")
        logger.info(f"👤 Member Agent IDs: {request.memberAgentIds}")
        logger.info(f"📝 Prompt: {request.prompt[:100]}...")
        
        # Step 1: Validate host agent exists
        host_agent = await validate_agent_exists(request.hostAgentId, is_host=True)
        logger.info(f"✅ Host agent validated: {host_agent.get('name', 'Unknown')}")
        
        # Step 2: Validate all member agents exist
        logger.info(f"🔍 Validating {len(request.memberAgentIds)} member agents...")
        member_agents = []
        for agent_id in request.memberAgentIds:
            agent = await validate_agent_exists(agent_id, is_host=False)
            member_agents.append(agent)
            logger.info(f"   ✅ {agent.get('name', 'Unknown')} (ID: {agent_id})")
        
        logger.info(f"✅ All member agents validated")
        
        # Step 3: Execute team with host coordination
        logger.info("🚀 Executing team with host coordination...")
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
                response=result.get("content", "No response generated"),
                mode="team",
                agents_used=all_agents,
                status="completed",
                execution_time=execution_time,
                message="Team executed successfully with host coordination"
            )
        else:
            logger.error(f"❌ Team execution failed: {result.get('message')}")
            return ExecutionResponse(
                response=result.get("content", ""),
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

