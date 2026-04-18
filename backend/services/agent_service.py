"""
Agent Service - Business logic for agent management.
Handles creation, updating, validation, and retrieval of agents.
"""

import logging
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from connection import get_session
from models.agent import Agent, HostAgent

logger = logging.getLogger(__name__)


class AgentService:
    """Service for managing agent operations"""
    
    # ============= AGENT CREATION =============
    
    @staticmethod
    def create_agent(
        name: str,
        config: Dict[str, Any],
        agent_type: str = "simple",
        description: str = None,
        is_mcp: bool = False,
        mcp_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create a new agent in the database.
        
        Args:
            name: Unique name for the agent
            config: Full agent configuration (JSON) with all fields like model_config, instructions, tools, etc.
            agent_type: Type of agent (simple, mcp, host)
            description: Human-readable description
            is_mcp: Whether this is an MCP agent
            mcp_config: MCP configuration (for MCP agents)
            
        Returns:
            Dict with created agent data
            
        Raises:
            ValueError: If validation fails
            Exception: If database operation fails
        """
        session: Session = None
        try:
            session = get_session()
            
            # Validate agent doesn't exist
            existing = session.query(Agent).filter(Agent.name == name).first()
            if existing:
                raise ValueError(f"Agent with name '{name}' already exists")
            
            # Create new agent
            agent = Agent(
                name=name,
                description=description,
                agent_type=agent_type,
                is_mcp=is_mcp,
                mcp_config=mcp_config or {},
                config=config,
                is_active=True
            )
            
            session.add(agent)
            session.commit()
            session.refresh(agent)
            
            logger.info(f"[OK] Created agent: {name} (ID: {agent.agent_id})")
            return agent.to_dict()
            
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"[ERROR] Error creating agent: {e}")
            raise
        finally:
            if session:
                session.close()
    
    # ============= AGENT UPDATE =============
    
    @staticmethod
    def update_agent(
        agent_id: int,
        name: str = None,
        description: str = None,
        config: Dict[str, Any] = None,
        mcp_config: Dict[str, Any] = None,
        is_active: bool = None
    ) -> Dict[str, Any]:
        """
        Update an existing agent.
        
        Args:
            agent_id: ID of agent to update
            name: (Optional) New name
            description: (Optional) New description
            config: (Optional) Updated configuration
            mcp_config: (Optional) Updated MCP configuration
            is_active: (Optional) Active status
            
        Returns:
            Dict with updated agent data
            
        Raises:
            ValueError: If agent not found
            Exception: If database operation fails
        """
        session: Session = None
        try:
            session = get_session()
            
            agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
            if not agent:
                raise ValueError(f"Agent with ID {agent_id} not found")
            
            # Update fields if provided
            if name is not None:
                # Check if new name already exists
                existing = session.query(Agent).filter(
                    Agent.name == name,
                    Agent.agent_id != agent_id
                ).first()
                if existing:
                    raise ValueError(f"Agent name '{name}' already taken")
                agent.name = name
            
            if description is not None:
                agent.description = description
            if config is not None:
                agent.config = config
            if mcp_config is not None:
                agent.mcp_config = mcp_config
            if is_active is not None:
                agent.is_active = is_active
            
            session.commit()
            session.refresh(agent)
            
            logger.info(f"[OK] Updated agent: {agent.name} (ID: {agent.agent_id})")
            return agent.to_dict()
            
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"[ERROR] Error updating agent: {e}")
            raise
        finally:
            if session:
                session.close()
    
    # ============= AGENT DELETION =============
    
    @staticmethod
    def delete_agent(agent_id: int) -> bool:
        """
        Delete an agent from the database.
        
        Args:
            agent_id: ID of agent to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            Exception: If database operation fails
        """
        session: Session = None
        try:
            session = get_session()
            
            agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found")
                return False
            
            session.delete(agent)
            session.commit()
            
            logger.info(f"[OK] Deleted agent: {agent.name} (ID: {agent.agent_id})")
            return True
            
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"[ERROR] Error deleting agent: {e}")
            raise
        finally:
            if session:
                session.close()


class HostAgentService:
    """Service for managing host/orchestrator agents"""
    
    @staticmethod
    def create_host_agent(
        name: str,
        config: Dict[str, Any],
        description: str = None,
        mode: str = "coordinate"
    ) -> Dict[str, Any]:
        """
        Create a new host agent.
        
        Args:
            name: Unique name for the host agent
            config: Full configuration including model_config, instructions, additional_params
            description: Description
            mode: Coordination mode (coordinate, sequential, parallel)
            
        Returns:
            Dict with created host agent data
        """
        session: Session = None
        try:
            session = get_session()
            
            # Check if exists
            existing = session.query(HostAgent).filter(HostAgent.name == name).first()
            if existing:
                raise ValueError(f"Host agent with name '{name}' already exists")
            
            host_agent = HostAgent(
                name=name,
                description=description,
                mode=mode,
                config=config,
                is_active=True
            )
            
            session.add(host_agent)
            session.commit()
            session.refresh(host_agent)
            
            logger.info(f"[OK] Created host agent: {name} (ID: {host_agent.agent_id})")
            return host_agent.to_dict()
            
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"[ERROR] Error creating host agent: {e}")
            raise
        finally:
            if session:
                session.close()

