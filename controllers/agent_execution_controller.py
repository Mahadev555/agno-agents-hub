"""
Agent Execution Controller
Handles execution of agent tasks with dynamic configurations.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from fastapi import HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentExecutionController:
    """Controller for executing agent tasks"""
    
    @staticmethod
    async def execute_agent_task(prompt: str, agent_ids: Optional[list[int]] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute an agent task with the provided prompt and optional parameters.
        
        Args:
            prompt (str): The prompt/task for the agent to execute
            agent_ids (Optional[list[int]], optional): List of agent IDs to use for execution
            **kwargs: Optional parameters for the task
            
        Returns:
            Dict[str, Any]: The result of the task execution
            
        Raises:
            HTTPException: If task execution fails
        """
        try:
            logger.info(f"Starting agent task execution with prompt: {prompt[:100]}...")
            
            # Import here to avoid circular imports
            from agents.subhost.agent import run_agent_task
            
            # Execute the agent task and get the result
            logger.info(f"Executing agent task with agent_ids: {agent_ids}...")
            result = await run_agent_task(prompt=prompt, agent_ids=agent_ids, **kwargs)

            logger.info("Agent task completed successfully")
            
            # Return the result from the agent workflow
            return result
            
        except Exception as e:
            logger.error(f"Error executing agent task: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to execute agent task: {str(e)}"
            )
  