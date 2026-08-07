"""
Database service module for handling all database operations.
Provides a centralized service layer for agent data access.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from connection import get_session
from models.agent import Agent, HostAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseService:
    """Service class for database operations"""
    
    # ============= AGENT OPERATIONS =============
    
    @staticmethod
    def get_all_agents() -> List[Dict[str, Any]]:
        """
        Retrieve all agents from the agents table.
        
        Returns:
            List[Dict[str, Any]]: List of agent records with all fields
            
        Raises:
            Exception: If database operation fails
        """
        session: Session = None
        try:
            session = get_session()
            agents = session.query(Agent).order_by(Agent.agent_id).all()
            result = [agent.to_dict() for agent in agents]
            logger.info(f"Retrieved {len(result)} agents from database")
            return result
        except Exception as e:
            logger.error(f"Error retrieving agents: {e}")
            raise
        finally:
            if session:
                session.close()
    
    @staticmethod
    def get_agent_by_id(agent_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific agent by ID.
        
        Args:
            agent_id (int): The ID of the agent to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Agent record if found, None otherwise
            
        Raises:
            Exception: If database operation fails
        """
        session: Session = None
        try:
            session = get_session()
            agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
            
            if agent:
                logger.info(f"Retrieved agent with ID {agent_id}")
                return agent.to_dict()
            else:
                logger.warning(f"Agent with ID {agent_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving agent {agent_id}: {e}")
            raise
        finally:
            if session:
                session.close()
    
    @staticmethod
    def get_agent_by_name(name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific agent by name.
        
        Args:
            name (str): The name of the agent to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Agent record if found, None otherwise
            
        Raises:
            Exception: If database operation fails
        """
        session: Session = None
        try:
            session = get_session()
            agent = session.query(Agent).filter(Agent.name == name).first()
            
            if agent:
                logger.info(f"Retrieved agent with name '{name}'")
                return agent.to_dict()
            else:
                logger.warning(f"Agent with name '{name}' not found")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving agent by name '{name}': {e}")
            raise
        finally:
            if session:
                session.close()
    
    @staticmethod
    def get_agents_by_ids(agent_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Retrieve multiple agents in a single query.

        Args:
            agent_ids (List[int]): The IDs to fetch

        Returns:
            List[Dict[str, Any]]: Found agents, ordered to match agent_ids.
                Missing IDs are simply absent; callers should compare lengths
                or diff the ids to detect them.
        """
        if not agent_ids:
            return []

        session: Session = None
        try:
            session = get_session()
            agents = session.query(Agent).filter(Agent.agent_id.in_(agent_ids)).all()
            by_id = {agent.agent_id: agent.to_dict() for agent in agents}

            # Preserve caller ordering; it determines team member order.
            result = [by_id[agent_id] for agent_id in agent_ids if agent_id in by_id]
            logger.info(f"Retrieved {len(result)}/{len(agent_ids)} agents in one query")
            return result
        except Exception as e:
            logger.error(f"Error retrieving agents by ids {agent_ids}: {e}")
            raise
        finally:
            if session:
                session.close()

    @staticmethod
    def get_agent_config(agent_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the configuration of a specific agent.
        
        Args:
            agent_id (int): The ID of the agent
            
        Returns:
            Optional[Dict[str, Any]]: Agent configuration if found, None otherwise
        """
        agent = DatabaseService.get_agent_by_id(agent_id)
        return agent['config'] if agent else None
    
    @staticmethod
    def get_active_agents() -> List[Dict[str, Any]]:
        """
        Retrieve all active agents.
        
        Returns:
            List[Dict[str, Any]]: List of active agent records
            
        Raises:
            Exception: If database operation fails
        """
        session: Session = None
        try:
            session = get_session()
            agents = session.query(Agent).filter(Agent.is_active == True).order_by(Agent.agent_id).all()
            result = [agent.to_dict() for agent in agents]
            logger.info(f"Retrieved {len(result)} active agents from database")
            return result
        except Exception as e:
            logger.error(f"Error retrieving active agents: {e}")
            raise
        finally:
            if session:
                session.close()
    
    @staticmethod
    def get_agents_by_type(agent_type: str) -> List[Dict[str, Any]]:
        """
        Retrieve agents by type.
        
        Args:
            agent_type (str): Type of agents to retrieve (simple, mcp, host)
            
        Returns:
            List[Dict[str, Any]]: List of agents of specified type
            
        Raises:
            Exception: If database operation fails
        """
        session: Session = None
        try:
            session = get_session()
            agents = session.query(Agent).filter(
                Agent.agent_type == agent_type,
                Agent.is_active == True
            ).order_by(Agent.agent_id).all()
            result = [agent.to_dict() for agent in agents]
            logger.info(f"Retrieved {len(result)} {agent_type} agents from database")
            return result
        except Exception as e:
            logger.error(f"Error retrieving agents by type '{agent_type}': {e}")
            raise
        finally:
            if session:
                session.close()
    
    @staticmethod
    def get_mcp_agents() -> List[Dict[str, Any]]:
        """
        Retrieve all MCP agents.
        
        Returns:
            List[Dict[str, Any]]: List of MCP agents
        """
        return DatabaseService.get_agents_by_type("mcp")
    
    # ============= HOST AGENT OPERATIONS =============
    
    @staticmethod
    def get_all_host_agents() -> List[Dict[str, Any]]:
        """
        Retrieve all host agents from the host_agent table.
        
        Returns:
            List[Dict[str, Any]]: List of host agent records
            
        Raises:
            Exception: If database operation fails
        """
        session: Session = None
        try:
            session = get_session()
            host_agents = session.query(HostAgent).order_by(HostAgent.agent_id).all()
            result = [host_agent.to_dict() for host_agent in host_agents]
            logger.info(f"Retrieved {len(result)} host agents from database")
            return result
        except Exception as e:
            logger.error(f"Error retrieving host agents: {e}")
            raise
        finally:
            if session:
                session.close()
    
    @staticmethod
    def get_host_agent_by_id(agent_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific host agent by ID.
        
        Args:
            agent_id (int): The ID of the host agent to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Host agent record if found, None otherwise
            
        Raises:
            Exception: If database operation fails
        """
        session: Session = None
        try:
            session = get_session()
            host_agent = session.query(HostAgent).filter(HostAgent.agent_id == agent_id).first()
            
            if host_agent:
                logger.info(f"Retrieved host agent with ID {agent_id}")
                return host_agent.to_dict()
            else:
                logger.warning(f"Host agent with ID {agent_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving host agent {agent_id}: {e}")
            raise
        finally:
            if session:
                session.close()
    
    @staticmethod
    def get_host_agent_by_name(name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific host agent by name.
        
        Args:
            name (str): The name of the host agent to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Host agent record if found, None otherwise
            
        Raises:
            Exception: If database operation fails
        """
        session: Session = None
        try:
            session = get_session()
            host_agent = session.query(HostAgent).filter(
                HostAgent.name.ilike(name)
            ).first()
            
            if host_agent:
                logger.info(f"Retrieved host agent with name '{name}'")
                return host_agent.to_dict()
            else:
                logger.warning(f"Host agent with name '{name}' not found")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving host agent by name '{name}': {e}")
            raise
        finally:
            if session:
                session.close()
    
    @staticmethod
    def get_host_agent_config(agent_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the configuration of a specific host agent.
        
        Args:
            agent_id (int): The ID of the host agent
            
        Returns:
            Optional[Dict[str, Any]]: Host agent configuration if found, None otherwise
        """
        host_agent = DatabaseService.get_host_agent_by_id(agent_id)
        return host_agent['config'] if host_agent else None
    
    @staticmethod
    def get_host_agent_config_by_name(name: str) -> Optional[Dict[str, Any]]:
        """
        Get host agent configuration by name.
        
        Args:
            name (str): Name of the host agent
            
        Returns:
            Optional[Dict[str, Any]]: Host agent configuration if found, None otherwise
        """
        host_agent = DatabaseService.get_host_agent_by_name(name)
        return host_agent['config'] if host_agent else None
