"""
Agent Execution Controller
Handles execution of agent tasks with dynamic configurations.
Supports both specific agents (by ID) and all available agents.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from fastapi import HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentExecutionController:
    """Controller for executing agent tasks"""
    
    @staticmethod
    async def execute_agent_task(
        prompt: str, 
        agent_ids: Optional[List[int]] = None, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute an agent task with the provided prompt and optional agent IDs.
        
        Flow:
        1. Validate inputs
        2. Load agent configurations from database (by IDs or all)
        3. Create agents dynamically from configs
        4. Execute the task with the dynamic team
        5. Return response
        
        Args:
            prompt (str): The prompt/task for the agent to execute
            agent_ids (Optional[List[int]], optional): List of specific agent IDs to use.
                                                       If None, uses all available agents.
            **kwargs: Additional parameters for the task
            
        Returns:
            Dict[str, Any]: Result dict with keys:
                - status: "completed" or "error"
                - message: Status message
                - content: Response from the agents
                - prompt: The input prompt
                - agent_ids: The agent IDs used
                - parameters: Additional parameters
            
        Raises:
            HTTPException: If task execution fails
        """
        try:
            logger.info("=" * 80)
            logger.info("🔄 AGENT EXECUTION CONTROLLER - STARTING TASK EXECUTION")
            logger.info("=" * 80)
            
            logger.info(f"📋 Task Details:")
            logger.info(f"   Prompt: {prompt[:100]}...")
            logger.info(f"   Specific Agent IDs: {agent_ids if agent_ids else 'All agents'}")
            logger.info(f"   Additional Parameters: {list(kwargs.keys())}")
            
            # Import here to avoid circular imports
            from agents.subhost.agent import run_agent_task
            
            # Execute the agent task with agent_ids
            logger.info(f"\n🚀 Executing agent task...")
            logger.info(f"   Agent IDs: {agent_ids}")
            
            result = await run_agent_task(
                prompt=prompt, 
                agent_ids=agent_ids, 
                **kwargs
            )
            
            logger.info(f"\n✅ Agent task completed successfully")
            logger.info(f"   Status: {result.get('status')}")
            logger.info(f"   Message: {result.get('message')}")
            if result.get('content'):
                logger.info(f"   Response Length: {len(str(result.get('content')))} chars")
            
            logger.info("=" * 80)
            
            # Return the result from the agent workflow
            return result
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ ERROR executing agent task:")
            logger.error(f"   Exception: {type(e).__name__}: {str(e)}")
            logger.error("=" * 80)
            
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to execute agent task: {str(e)}"
            )
    
    @staticmethod
    async def execute_single_agent(
        prompt: str, 
        agent_id: int
    ) -> Dict[str, Any]:
        """
        Execute a single agent directly.
        
        Args:
            prompt (str): The prompt/task for the agent
            agent_id (int): ID of the agent to execute
            
        Returns:
            Dict[str, Any]: Result dict with execution details
        """
        try:
            logger.info(f"🎯 Executing single agent {agent_id}")
            
            from agents.subhost.agent import run_agent_task
            
            # Run agent with single agent ID
            result = await run_agent_task(
                prompt=prompt,
                agent_ids=[agent_id],
                execution_mode="single"
            )
            
            logger.info(f"✅ Single agent execution complete")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error executing single agent: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to execute agent: {str(e)}"
            )
    
    @staticmethod
    async def execute_team(
        prompt: str,
        host_agent_id: int,
        member_agent_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Execute a team with host agent coordination.
        
        The host agent coordinates the team, divides tasks among members,
        and consolidates the final response.
        
        Args:
            prompt (str): The prompt/task for the team
            host_agent_id (int): ID of the host/coordinator agent
            member_agent_ids (List[int]): IDs of member agents
            
        Returns:
            Dict[str, Any]: Result dict with consolidated response
        """
        try:
            logger.info(f"👥 Executing team with host agent {host_agent_id}")
            logger.info(f"   Members: {member_agent_ids}")
            
            from agents.subhost.agent import run_agent_task
            
            # Run team with host agent coordinating
            result = await run_agent_task(
                prompt=prompt,
                agent_ids=member_agent_ids,
                host_agent_id=host_agent_id,
                execution_mode="team"
            )
            
            logger.info(f"✅ Team execution complete")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error executing team: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to execute team: {str(e)}"
            )