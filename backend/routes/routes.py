from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel
from controllers.agents_controller import (
    AgentsController,
    HostAgentsController,
    AgentCreateRequest,
    AgentUpdateRequest,
    HostAgentCreateRequest,
)
from controllers.agent_execution_controller import AgentExecutionController

# Pydantic models for our new endpoints
class ChatMessage(BaseModel):
    message: str
    agentId: Optional[str | List[str]] = None

class AgentExecution(BaseModel):
    agentId: str
    parameters: Dict[str, Any]

router = APIRouter()


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

@router.post("/api/chat")
async def process_chat(request: Request):
    """Process a chat message using agents"""
    try:
        body = await request.json()
        prompt = body.get("prompt")
        agent_ids = body.get("agentIds")
        
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        if agent_ids:
            result = await AgentExecutionController.execute_agent_task(
                prompt=prompt,
                agent_ids=agent_ids
            )
            return {
                "response": result.get("content", "No response generated"),
                "agent": agent_ids,
                "status": result.get("status", "completed")
            }
        else:
            result = await AgentExecutionController.execute_agent_task(prompt=prompt)
            return {
                "response": result.get("content", "No response generated"),
                "agent": None,
                "status": result.get("status", "completed")
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

