"""
Agents Controller

Handles agent management for both workers and coordinators.

Every read is filtered to what the caller may see and every write is checked
against ownership, so authorization cannot be forgotten at the route layer.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from dependencies import can_read, require_owner
from services.agent_service import AgentService, ConfigError, HostAgentService
from services.database_service import DatabaseService

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
    owner_id: Optional[int] = None
    is_public: bool = False
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
    is_public: Optional[bool] = False


class AgentUpdateRequest(BaseModel):
    """Request model for updating agent details"""
    name: Optional[str] = None
    description: Optional[str] = None
    mcp_config: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class HostAgentResponse(BaseModel):
    """Response model for host agent data"""
    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(alias="agent_id")
    name: str
    description: Optional[str] = None
    is_mcp: bool
    is_active: bool = True
    owner_id: Optional[int] = None
    is_public: bool = False
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


def _visible(records: List[Dict[str, Any]], user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Keep only what this user may read: their own, public, or unowned."""
    return [r for r in records if can_read(r, user)]


class AgentsController:
    """Controller class for handling agent-related operations"""

    @staticmethod
    async def get_all_agents(user: Dict[str, Any]) -> List[AgentResponse]:
        """Get every agent the caller may see."""
        try:
            agents = DatabaseService.get_all_agents()
            return [AgentResponse(**a) for a in _visible(agents, user)]
        except Exception as e:
            logger.error(f"Error retrieving all agents: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve agents: {str(e)}")

    @staticmethod
    async def get_active_agents(user: Dict[str, Any]) -> List[AgentResponse]:
        """Get active agents the caller may see."""
        try:
            agents = DatabaseService.get_active_agents()
            return [AgentResponse(**a) for a in _visible(agents, user)]
        except Exception as e:
            logger.error(f"Error retrieving active agents: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_agents_by_type(agent_type: str, user: Dict[str, Any]) -> List[AgentResponse]:
        """Get agents of one kind that the caller may see."""
        try:
            agents = DatabaseService.get_agents_by_type(agent_type)
            return [AgentResponse(**a) for a in _visible(agents, user)]
        except Exception as e:
            logger.error(f"Error retrieving {agent_type} agents: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_agent_by_id(agent_id: int, user: Dict[str, Any]) -> AgentResponse:
        """
        Get one agent.

        An agent the caller may not see returns 404 rather than 403, so the
        endpoint cannot be used to discover which ids exist.
        """
        try:
            agent = DatabaseService.get_agent_by_id(agent_id)
            if not agent or not can_read(agent, user):
                raise HTTPException(status_code=404, detail=f"Agent with ID {agent_id} not found")
            return AgentResponse(**agent)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving agent {agent_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_agent_by_name(name: str, user: Dict[str, Any]) -> AgentResponse:
        """Get an agent by name, if the caller may see it."""
        try:
            agent = DatabaseService.get_agent_by_name(name)
            if not agent or not can_read(agent, user):
                raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
            return AgentResponse(**agent)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving agent by name: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def create_agent(agent_data: AgentCreateRequest, user: Dict[str, Any]) -> AgentResponse:
        """
        Create a new agent owned by the caller.

        Defaults and validation live in the AgentConfig schema, so this no
        longer hand-patches eight keys onto the config dict.
        """
        try:
            config = dict(agent_data.config or {})
            if agent_data.instructions:
                config["instructions"] = agent_data.instructions

            created_agent = AgentService.create_agent(
                name=agent_data.name,
                description=agent_data.description,
                kind=agent_data.agent_type,
                is_mcp=agent_data.is_mcp,
                agent_type=agent_data.agent_type,
                mcp_config=agent_data.mcp_config,
                config=config,
                owner_id=user["user_id"],
                is_public=bool(agent_data.is_public),
            )
            return AgentResponse(**created_agent)
        except ConfigError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def update_agent(
        agent_id: int, agent_data: AgentUpdateRequest, user: Dict[str, Any]
    ) -> AgentResponse:
        """Update an agent the caller owns."""
        existing = DatabaseService.get_agent_by_id(agent_id)
        if not existing or not can_read(existing, user):
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        require_owner(existing, user, "agent")

        try:
            update_kwargs = {k: v for k, v in agent_data.dict().items() if v is not None}
            updated_agent = AgentService.update_agent(agent_id, **update_kwargs)
            return AgentResponse(**updated_agent)
        except ConfigError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def delete_agent(agent_id: int, user: Dict[str, Any]) -> Dict[str, str]:
        """Delete an agent the caller owns."""
        existing = DatabaseService.get_agent_by_id(agent_id)
        if not existing or not can_read(existing, user):
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        require_owner(existing, user, "agent")

        try:
            deleted = AgentService.delete_agent(agent_id)
            if not deleted:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
            return {"message": f"Agent {agent_id} deleted successfully"}
        except ConfigError as e:
            # e.g. the agent still coordinates a team
            raise HTTPException(status_code=409, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ============= HOST AGENT CONTROLLER =============

class HostAgentsController:
    """Coordinators are agents with kind='host'; these endpoints predate that."""

    @staticmethod
    async def get_all_host_agents(user: Dict[str, Any]) -> List[HostAgentResponse]:
        """Get coordinators the caller may see."""
        try:
            host_agents = DatabaseService.get_all_host_agents()
            return [HostAgentResponse(**a) for a in _visible(host_agents, user)]
        except Exception as e:
            logger.error(f"Error retrieving all host agents: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_host_agent_by_id(agent_id: int, user: Dict[str, Any]) -> HostAgentResponse:
        """Get one coordinator."""
        try:
            agent = DatabaseService.get_host_agent_by_id(agent_id)
            if not agent or not can_read(agent, user):
                raise HTTPException(status_code=404, detail=f"Host agent {agent_id} not found")
            return HostAgentResponse(**agent)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving host agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def create_host_agent(
        agent_data: HostAgentCreateRequest, user: Dict[str, Any]
    ) -> HostAgentResponse:
        """Create a coordinator owned by the caller."""
        try:
            created_agent = HostAgentService.create_host_agent(
                name=agent_data.name,
                description=agent_data.description,
                mode=agent_data.mode,
                config=agent_data.config,
                owner_id=user["user_id"],
            )
            return HostAgentResponse(**created_agent)
        except ConfigError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating host agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))
