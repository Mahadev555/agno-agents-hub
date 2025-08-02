"""
Agent model functions for database operations using PostgreSQL cursor and connection.
This module provides functions to interact with the agents and host_agent tables.
"""

import json
import logging
from typing import List, Dict, Optional, Any
from connection import get_connection
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentModel:
    """Model class for agent database operations"""
    
    @staticmethod
    def get_all_agents() -> List[Dict[str, Any]]:
        """
        Retrieve all agents from the agents table.
        
        Returns:
            List[Dict[str, Any]]: List of agent records with all fields
            
        Raises:
            psycopg2.Error: If database operation fails
        """
        try:
            conn = get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT agent_id, name, description, is_mcp, config 
                    FROM agents 
                    ORDER BY agent_id
                """)
                agents = cursor.fetchall()
                
                # Convert RealDictRow to regular dict and ensure config is properly parsed
                result = []
                for agent in agents:
                    agent_dict = dict(agent)
                    # Ensure config is a dict (it should already be from JSONB)
                    if isinstance(agent_dict['config'], str):
                        agent_dict['config'] = json.loads(agent_dict['config'])
                    result.append(agent_dict)
                
                logger.info(f"Retrieved {len(result)} agents from database")
                return result
                
        except psycopg2.Error as e:
            logger.error(f"Error retrieving agents: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def get_agent_by_id(agent_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific agent by ID.
        
        Args:
            agent_id (int): The ID of the agent to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Agent record if found, None otherwise
            
        Raises:
            psycopg2.Error: If database operation fails
        """
        try:
            conn = get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT agent_id, name, description, is_mcp, config 
                    FROM agents 
                    WHERE agent_id = %s
                """, (agent_id,))
                agent = cursor.fetchone()
                
                if agent:
                    agent_dict = dict(agent)
                    # Ensure config is a dict
                    if isinstance(agent_dict['config'], str):
                        agent_dict['config'] = json.loads(agent_dict['config'])
                    logger.info(f"Retrieved agent with ID {agent_id}")
                    return agent_dict
                else:
                    logger.warning(f"Agent with ID {agent_id} not found")
                    return None
                    
        except psycopg2.Error as e:
            logger.error(f"Error retrieving agent {agent_id}: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    

class HostAgentModel:
    """Model class for host agent database operations"""
    
    @staticmethod
    def get_all_host_agents() -> List[Dict[str, Any]]:
        """
        Retrieve all host agents from the host_agent table.
        
        Returns:
            List[Dict[str, Any]]: List of host agent records
            
        Raises:
            psycopg2.Error: If database operation fails
        """
        try:
            conn = get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT agent_id, name, description, is_mcp, config 
                    FROM host_agent 
                    ORDER BY agent_id
                """)
                host_agents = cursor.fetchall()
                
                result = []
                for agent in host_agents:
                    agent_dict = dict(agent)
                    if isinstance(agent_dict['config'], str):
                        agent_dict['config'] = json.loads(agent_dict['config'])
                    result.append(agent_dict)
                
                logger.info(f"Retrieved {len(result)} host agents from database")
                return result
                
        except psycopg2.Error as e:
            logger.error(f"Error retrieving host agents: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def get_host_agent_by_id(agent_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific host agent by ID.
        
        Args:
            agent_id (int): The ID of the host agent to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Host agent record if found, None otherwise
            
        Raises:
            psycopg2.Error: If database operation fails
        """
        try:
            conn = get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT agent_id, name, description, is_mcp, config 
                    FROM host_agent 
                    WHERE agent_id = %s
                """, (agent_id,))
                agent = cursor.fetchone()
                
                if agent:
                    agent_dict = dict(agent)
                    if isinstance(agent_dict['config'], str):
                        agent_dict['config'] = json.loads(agent_dict['config'])
                    logger.info(f"Retrieved host agent with ID {agent_id}")
                    return agent_dict
                else:
                    logger.warning(f"Host agent with ID {agent_id} not found")
                    return None
                    
        except psycopg2.Error as e:
            logger.error(f"Error retrieving host agent {agent_id}: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    
def get_agent_config(agent_id: int, is_host_agent: bool = False) -> Optional[Dict[str, Any]]:
    """
    Get the configuration of a specific agent.
    
    Args:
        agent_id (int): The ID of the agent
        is_host_agent (bool): Whether to look in the host_agent table
        
    Returns:
        Optional[Dict[str, Any]]: Agent configuration if found, None otherwise
    """
    if is_host_agent:
        agent = HostAgentModel.get_host_agent_by_id(agent_id)
    else:
        agent = AgentModel.get_agent_by_id(agent_id)
    
    return agent['config'] if agent else None


def get_all_agent_configs() -> Dict[str, Any]:
    """
    Get configurations for all agents organized by type.
    
    Returns:
        Dict[str, Any]: Dictionary containing all agent configurations
    """
    try:
        # Get all regular agents
        all_agents_configs = AgentModel.get_all_agents()
        
        return all_agents_configs
        
    except Exception as e:
        logger.error(f"Error retrieving all agent configs: {e}")
        raise


def get_agent_configs_for_dynamic_team() -> Dict[str, Any]:
    """
    Get agent configurations formatted for dynamic team creation.
    
    Returns:
        Dict[str, Any]: Formatted configurations for team creation
    """
    try:
        all_configs = get_all_agent_configs()
        
        # Format for dynamic team - similar to subhost_config.json structure
        team_configs = {
            "agents": []
        }
        
        # Add MCP agents
        for name, config in all_configs["mcp_agents"].items():
            team_configs["agents"].append({
                "name": name,
                "type": "mcp",
                "config": config
            })
        
        # Add simple agents
        for name, config in all_configs["simple_agents"].items():
            team_configs["agents"].append({
                "name": name,
                "type": "simple",
                "config": config
            })
        
        logger.info(f"Formatted {len(team_configs['agents'])} agent configs for dynamic team")
        return team_configs
        
    except Exception as e:
        logger.error(f"Error formatting agent configs for dynamic team: {e}")
        raise


def get_host_agent_config_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Get host agent configuration by name.
    
    Args:
        name (str): Name of the host agent
        
    Returns:
        Optional[Dict[str, Any]]: Host agent configuration if found, None otherwise
    """
    try:
        host_agents = HostAgentModel.get_all_host_agents()
        
        for agent in host_agents:
            if agent["name"].lower() == name.lower():
                return agent["config"]
        
        logger.warning(f"Host agent with name '{name}' not found")
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving host agent config by name '{name}': {e}")
        raise


def get_agent_configs_by_ids(agent_ids: List[str]) -> Dict[str, Any]:
    """
    Get configurations for specific agents by their IDs.
    
    Args:
        agent_ids (List[str]): List of agent IDs in the format "type_id" (e.g. "mcp_1", "simple_2")
        
    Returns:
        Dict[str, Any]: Dictionary containing selected agent configurations
    """
    try:
        # Get all agent configs first
        all_configs = get_all_agent_configs()
       
        return all_configs
        
    except Exception as e:
        logger.error(f"Error retrieving agent configs by IDs: {e}")
        raise
