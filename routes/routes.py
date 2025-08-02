from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel
from controllers.agents_controller import (
    AgentsController
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


# ======================= AGENT ROUTES =======================

@router.get("/api/agents")
async def get_agents_for_client():
    """Get all available agents for the client"""
    try:
        # Try to get agents from the database first
        db_agents = await AgentsController.get_all_agents()
        
        # If we have agents in the database, format them for the client
        if db_agents:
            formatted_agents = []
            for agent in db_agents:
                formatted_agent = {
                    "id": str(agent.id),
                    "name": agent.name,
                    "description": agent.description or "",
                    "parameters": []
                }
                formatted_agents.append(formatted_agent)
            return formatted_agents
        
        # Fallback to sample agents if no agents in the database
        raise HTTPException(status_code=404, detail="No agents found in database")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch agents: {str(e)}")

@router.get("/api/agents/{agent_id}")
async def get_agent_by_id(agent_id: int):
    """Get a specific agent by ID"""
    try:
        agent = await AgentsController.get_agent_by_id(agent_id)
        
        # Format the agent for the client
        formatted_agent = {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description or "",
            "is_mcp": agent.is_mcp,
            "config": agent.config,
            "parameters": []
        }
        return formatted_agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch agent: {str(e)}")

@router.post("/api/chat")
async def process_chat(request: Request):
    """Process a chat message"""
    try:
        # Get prompt and agentIds from request body
        body = await request.json()
        prompt = body.get("prompt")
        agent_ids = body.get("agentIds")
        
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        # Use the agent execution controller to process the message
        if agent_ids:
            # Execute with specific agent(s)
            result = await AgentExecutionController.execute_agent_task(
                prompt=prompt,
                agent_ids=agent_ids
            )
            return {
                "response": result.get("content", "I processed your request but didn't get a clear answer."),
                "agent": agent_ids,
                "status": result.get("status", "completed")
            }
        else:
            # No specific agent, use default
            result = await AgentExecutionController.execute_agent_task(
                prompt=prompt
            )
            return {
                "response": result.get("content", "I processed your request but didn't get a clear answer."),
                "agent": None,
                "status": result.get("status", "completed")
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat message: {str(e)}")

