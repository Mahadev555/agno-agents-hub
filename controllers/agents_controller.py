"""
Agents Controller
Handles business logic for agent management operations including both host agents and simple agents.
"""

import logging
from typing import List, Dict, Optional, Any
from fastapi import HTTPException
from models.agents_model import AgentModel, HostAgentModel
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic models for request/response validation
class AgentResponse(BaseModel):
    """Response model for agent data"""
    id: int = Field(alias="agent_id")  # Map database field agent_id to id for client compatibility
    name: str
    description: Optional[str] = None
    is_mcp: bool
    config: Dict[str, Any]
    
    class Config:
        allow_population_by_field_name = True


class AgentUpdateRequest(BaseModel):
    """Request model for updating agent details"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_mcp: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class AgentConfigUpdateRequest(BaseModel):
    """Request model for updating agent configuration only"""
    config: Dict[str, Any] = Field(..., description="New configuration for the agent")


class HostAgentResponse(BaseModel):
    """Response model for host agent data"""
    id: int = Field(alias="agent_id")  # Map database field agent_id to id for client compatibility
    name: str
    description: Optional[str] = None
    is_mcp: bool
    config: Dict[str, Any]
    
    class Config:
        allow_population_by_field_name = True


class HostAgentUpdateRequest(BaseModel):
    """Request model for updating host agent details"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_mcp: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class AgentsController:
    """Controller class for handling agent-related operations"""
    
    @staticmethod
    async def get_all_agents() -> List[AgentResponse]:
        """
        Get all agents from the database.
        
        Returns:
            List[AgentResponse]: List of all agents
            
        Raises:
            HTTPException: If database operation fails
        """
        try:
            agents = AgentModel.get_all_agents()
            return [AgentResponse(**agent) for agent in agents]
        except Exception as e:
            logger.error(f"Error retrieving all agents: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve agents: {str(e)}")
    
    @staticmethod
    async def get_agent_by_id(agent_id: int) -> AgentResponse:
        """
        Get a specific agent by ID.
        
        Args:
            agent_id (int): The ID of the agent to retrieve
            
        Returns:
            AgentResponse: The agent data
            
        Raises:
            HTTPException: If agent not found or database operation fails
        """
        try:
            agent = AgentModel.get_agent_by_id(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found")
            return AgentResponse(**agent)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving agent {agent_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve agent: {str(e)}")
    
    
class HostAgentsController:
    """Controller class for handling host agent-related operations"""
    
    @staticmethod
    async def get_all_host_agents() -> List[HostAgentResponse]:
        """
        Get all host agents from the database.
        
        Returns:
            List[HostAgentResponse]: List of all host agents
            
        Raises:
            HTTPException: If database operation fails
        """
        try:
            host_agents = HostAgentModel.get_all_host_agents()
            return [HostAgentResponse(**agent) for agent in host_agents]
        except Exception as e:
            logger.error(f"Error retrieving all host agents: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve host agents: {str(e)}")
    
    @staticmethod
    async def get_host_agent_by_id(agent_id: int) -> HostAgentResponse:
        """
        Get a specific host agent by ID.
        
        Args:
            agent_id (int): The ID of the host agent to retrieve
            
        Returns:
            HostAgentResponse: The host agent data
            
        Raises:
            HTTPException: If host agent not found or database operation fails
        """
        try:
            agent = HostAgentModel.get_host_agent_by_id(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail=f"Host agent with ID {agent_id} not found")
            return HostAgentResponse(**agent)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving host agent {agent_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve host agent: {str(e)}")
    

