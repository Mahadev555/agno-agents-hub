"""
Agents Controller
Handles business logic for agent management operations including both host agents and simple agents.
"""

import logging
from typing import List, Dict, Optional, Any
from fastapi import HTTPException
from services.database_service import DatabaseService
from services.agent_service import AgentService, HostAgentService
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# ============= PYDANTIC MODELS =============

class AgentResponse(BaseModel):
    """Response model for agent data"""
    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(alias="agent_id")
    name: str
    description: Optional[str] = None
    agent_type: str = "simple"
    is_mcp: bool
    is_active: bool = True
    mcp_config: Optional[Dict[str, Any]] = None
    config: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AgentCreateRequest(BaseModel):
    """Request model for creating an agent"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    agent_type: str = Field(default="simple")
    instructions: Optional[str] = None
    is_mcp: Optional[bool] = False
    mcp_config: Optional[Dict[str, Any]] = None
    config: Dict[str, Any]


class AgentUpdateRequest(BaseModel):
    """Request model for updating agent details"""
    name: Optional[str] = None
    description: Optional[str] = None
    mcp_config: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class HostAgentResponse(BaseModel):
    """Response model for host agent data"""
    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(alias="agent_id")
    name: str
    description: Optional[str] = None
    is_mcp: bool
    is_active: bool = True
    mode: str = "coordinate"
    config: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class HostAgentCreateRequest(BaseModel):
    """Request model for creating a host agent"""
    name: str
    description: Optional[str] = None
    mode: str = Field(default="coordinate")
    config: Dict[str, Any]


# ============= AGENT CONTROLLER =============

class AgentsController:
    """Controller class for handling agent-related operations"""
    
    @staticmethod
    async def get_all_agents() -> List[AgentResponse]:
        """Get all agents from the database"""
        try:
            agents = DatabaseService.get_all_agents()
            return [AgentResponse(**agent) for agent in agents]
        except Exception as e:
            logger.error(f"Error retrieving all agents: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve agents: {str(e)}")
    
    @staticmethod
    async def get_active_agents() -> List[AgentResponse]:
        """Get all active agents"""
        try:
            agents = DatabaseService.get_active_agents()
            return [AgentResponse(**agent) for agent in agents]
        except Exception as e:
            logger.error(f"Error retrieving active agents: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def get_agents_by_type(agent_type: str) -> List[AgentResponse]:
        """Get agents filtered by type"""
        try:
            agents = DatabaseService.get_agents_by_type(agent_type)
            return [AgentResponse(**agent) for agent in agents]
        except Exception as e:
            logger.error(f"Error retrieving {agent_type} agents: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def get_agent_by_id(agent_id: int) -> AgentResponse:
        """Get a specific agent by ID"""
        try:
            agent = DatabaseService.get_agent_by_id(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found")
            return AgentResponse(**agent)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving agent {agent_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def get_agent_by_name(name: str) -> AgentResponse:
        """Get agent by name"""
        try:
            agent = DatabaseService.get_agent_by_name(name)
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
            return AgentResponse(**agent)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving agent by name: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def create_agent(agent_data: AgentCreateRequest) -> AgentResponse:
        """Create a new agent"""
        try:
            # Ensure config has required fields
            config = agent_data.config or {}
            
            # Add instructions to config if provided
            if agent_data.instructions:
                config['instructions'] = agent_data.instructions
            
            # Ensure config has name
            if 'name' not in config:
                config['name'] = agent_data.name
            
            # Ensure config has description
            if 'description' not in config and agent_data.description:
                config['description'] = agent_data.description
            
            # Ensure model_config exists with required fields (id, type, max_tokens)
            if 'model_config' not in config:
                config['model_config'] = {
                    'id': 'gemini-2.5-flash-lite',
                    'type': 'google',
                    'max_tokens': 4096,
                }
            
            # Ensure tools array exists
            if 'tools' not in config:
                config['tools'] = []
            
            # Ensure role exists
            if 'role' not in config:
                config['role'] = 'Assistant'
            
            # Ensure markdown flag exists
            if 'markdown' not in config:
                config['markdown'] = True
            
            # Ensure show_tool_calls flag exists
            if 'show_tool_calls' not in config:
                config['show_tool_calls'] = True
            
            # Ensure additional_params exists
            if 'additional_params' not in config:
                config['additional_params'] = {}
            
            created_agent = AgentService.create_agent(
                name=agent_data.name,
                description=agent_data.description,
                agent_type=agent_data.agent_type,
                is_mcp=agent_data.is_mcp,
                mcp_config=agent_data.mcp_config,
                config=config
            )
            return AgentResponse(**created_agent)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def update_agent(agent_id: int, agent_data: AgentUpdateRequest) -> AgentResponse:
        """Update an existing agent"""
        try:
            update_kwargs = {k: v for k, v in agent_data.dict().items() if v is not None}
            updated_agent = AgentService.update_agent(agent_id, **update_kwargs)
            return AgentResponse(**updated_agent)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def delete_agent(agent_id: int) -> Dict[str, str]:
        """Delete an agent"""
        try:
            deleted = AgentService.delete_agent(agent_id)
            if not deleted:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
            return {"message": f"Agent {agent_id} deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ============= HOST AGENT CONTROLLER =============

class HostAgentsController:
    """Controller class for handling host agent-related operations"""
    
    @staticmethod
    async def get_all_host_agents() -> List[HostAgentResponse]:
        """Get all host agents"""
        try:
            host_agents = DatabaseService.get_all_host_agents()
            return [HostAgentResponse(**agent) for agent in host_agents]
        except Exception as e:
            logger.error(f"Error retrieving all host agents: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def get_host_agent_by_id(agent_id: int) -> HostAgentResponse:
        """Get a specific host agent by ID"""
        try:
            agent = DatabaseService.get_host_agent_by_id(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail=f"Host agent {agent_id} not found")
            return HostAgentResponse(**agent)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving host agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    async def create_host_agent(agent_data: HostAgentCreateRequest) -> HostAgentResponse:
        """Create a new host agent"""
        try:
            created_agent = HostAgentService.create_host_agent(
                name=agent_data.name,
                description=agent_data.description,
                mode=agent_data.mode,
                config=agent_data.config
            )
            return HostAgentResponse(**created_agent)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating host agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    

