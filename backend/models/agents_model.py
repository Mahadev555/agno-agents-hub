"""
Agent model functions for retrieving agent configurations.
This module provides functions to fetch agent and host agent configurations
from the database for use in dynamic team creation.
"""

import logging
from typing import List, Dict, Optional, Any
from services.database_service import DatabaseService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        return DatabaseService.get_host_agent_config(agent_id)
    else:
        return DatabaseService.get_agent_config(agent_id)
    
    

def get_all_agent_configs() -> List[Dict[str, Any]]:
    """
    Get configurations for all agents.
    
    Returns:
        List[Dict[str, Any]]: List containing all agent configurations with their full data
    """
    try:
        # Get all active agents from database
        all_agents = DatabaseService.get_active_agents()
        logger.info(f"Retrieved {len(all_agents)} agent configurations from database")
        return all_agents
        
    except Exception as e:
        logger.error(f"Error retrieving all agent configs: {e}")
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
        host_agent = DatabaseService.get_host_agent_by_name(name)
        
        if host_agent:
            logger.info(f"Retrieved host agent config for '{name}'")
            return host_agent.get("config")
        
        logger.warning(f"Host agent with name '{name}' not found")
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving host agent config by name '{name}': {e}")
        raise


def get_agent_configs_by_ids(agent_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Get configurations for specific agents by their IDs.
    
    Args:
        agent_ids (List[int]): List of agent IDs
        
    Returns:
        List[Dict[str, Any]]: List of agent configurations for the specified IDs
    """
    try:
        configs = []
        for agent_id in agent_ids:
            agent = DatabaseService.get_agent_by_id(agent_id)
            if agent:
                configs.append(agent)
        
        logger.info(f"Retrieved {len(configs)} agent configurations by IDs")
        return configs
        
    except Exception as e:
        logger.error(f"Error retrieving agent configs by IDs: {e}")
        raise
