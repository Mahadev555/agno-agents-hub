import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import AsyncIterator, Dict, Any, Iterator
from agno.tools.mcp import MCPTools
from agno.agent import RunResponse, RunEvent
from agno.workflow import Workflow
from agno.storage.sqlite import SqliteStorage
from agno.utils.log import logger

# Add the project root to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.hosts.host_agent import create_dynamic_team_with_mcp
from models.agents_model import get_all_agent_configs, get_host_agent_config_by_name


class AgentWorkflow(Workflow):
    """Workflow for running dynamic agent teams"""
    
    def __init__(self, session_id: str = None, storage=None):
        """Initialize the workflow"""
        super().__init__(
            session_id=session_id or f"agent-session-{hash(str(asyncio.get_event_loop()))}",
            storage=storage or SqliteStorage(
                table_name="agent_workflows",
                db_file="tmp/agent_workflows.db",
            )
        )
        self.dynamic_team = None
        self.mcp_stack = None
    async def initialize_team(self, agent_ids=None, host_agent_id=None, execution_mode="single"):
        """Initialize the dynamic team with database configurations
        
        Args:
            agent_ids (List[int], optional): List of agent IDs to include in the team.
                                            If provided, creates a dynamic team with only these agents.
                                            If None, creates team with all available agents.
            host_agent_id (int, optional): ID of the host agent for team coordination mode
            execution_mode (str): "single" for single agent, "team" for team with host coordination
        """
        try:
            logger.info("📊 Loading agent configurations from database...")

            # Get agent configs based on agent_ids or all if none provided
            if agent_ids:
                from models.agents_model import get_agent_configs_by_ids
                agent_configs = get_agent_configs_by_ids(agent_ids)
                logger.info(f"🔍 Loading configurations for {len(agent_ids)} specific agents (IDs: {agent_ids})")
                
                if execution_mode == "team" and host_agent_id:
                    # Team mode with host coordination
                    from models.agents_model import get_agent_configs_by_ids as get_host_config
                    from services.database_service import DatabaseService
                    
                    host_agent = DatabaseService.get_host_agent_by_id(host_agent_id)
                    if not host_agent:
                        raise ValueError(f"Host agent {host_agent_id} not found")
                    
                    team_config = host_agent.get("config", {})
                    logger.info(f"✅ Using host agent {host_agent.get('name')} for team coordination")
                else:
                    # Single agent or team without specific host config
                    team_config = {
                        "name": f"Dynamic Team - Agents {agent_ids}",
                        "mode": "coordinate" if execution_mode == "team" else "standalone",
                        "instructions": ["Execute the task with the selected agents"] if execution_mode == "team" else [],
                        "additional_params": {}
                    }
                    if execution_mode == "single":
                        logger.info(f"✅ Created single agent config")
                    else:
                        logger.info(f"✅ Created dynamic team config for specific agents")
            else:
                from models.agents_model import get_all_agent_configs
                agent_configs = get_all_agent_configs()
                logger.info("🔍 Loading configurations for all available agents")
                
                # Get host agent config for all agents
                team_config = get_host_agent_config_by_name("Mixed Agent Team")
                if not team_config:
                    raise ValueError("Host agent 'Mixed Agent Team' configuration not found in database")
                logger.info(f"✅ Using Mixed Agent Team config for all agents")
            
            logger.info(f"✅ Loaded {len(agent_configs)} agent configuration(s)")

            # Create async exit stack for MCP tools
            self.mcp_stack = AsyncExitStack()

            # Create dynamic team
            logger.info("🚀 Creating dynamic team...")
            self.dynamic_team = await create_dynamic_team_with_mcp(team_config, agent_configs)

            # Manage MCP tools lifecycle
            for agent in self.dynamic_team.members:
                if hasattr(agent, 'tools'):
                    for tool in agent.tools:
                        if isinstance(tool, MCPTools):
                            await self.mcp_stack.enter_async_context(tool)

            logger.info("✅ Dynamic team initialized successfully!")

        except Exception as e:
            logger.error(f"❌ Failed to initialize team: {e}", exc_info=True)
    def run(self, prompt: str, **kwargs) -> Iterator[RunResponse]:  
        """  
        Run the agent workflow with the given prompt.  
        
        Args:  
            prompt (str): The prompt for the agent to process  
            **kwargs: Additional parameters  
            
        Yields:  
            RunResponse: The response from the agent execution  
        """  
        try:  
            import asyncio  
            
            # Check if we're in an async context  
            in_async_context = False
            try:  
                asyncio.get_running_loop()
                in_async_context = True
            except RuntimeError:  
                # Not in an async context
                pass
                
            if in_async_context:
                # If we're in an async context, we can't use run_until_complete or asyncio.run
                # We need to create a synchronous version of the async function and run it
                async def async_wrapper():
                    return await self._async_run(prompt, **kwargs)
                
                # Execute the coroutine and get the result synchronously
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(lambda: asyncio.new_event_loop().run_until_complete(async_wrapper()))
                    result = future.result()
            else:
                # No running loop, we can create one  
                result = asyncio.run(self._async_run(prompt, **kwargs))  
                
            # Yield each response from the result list  
            for response in result:  
                yield response

            
                
        except Exception as e:  
            logger.error(f"Error in workflow run: {e}")  
            yield RunResponse(  
                event=RunEvent.workflow_completed,  
                content=f"Error in workflow execution: {str(e)}",  
            )  
    
    async def _async_run(self, prompt: str, **kwargs) -> list[RunResponse]:  
        """  
        Internal async method to run the agent workflow.  
        
        Args:  
            prompt (str): The prompt for the agent to process  
            **kwargs: Additional parameters  
            
        Returns:  
            list[RunResponse]: List of responses from the agent execution  
        """  
        responses = []  
        
        try:  
            # Initialize team if not already done  
            if not self.dynamic_team:  
                await self.initialize_team()  
            
            logger.info(f"💬 Processing request: {prompt[:100]}...")  
            
            # Execute the team task and capture response - USE ARUN for async agents  
            response = await self.dynamic_team.arun(prompt, **kwargs)  
    
            if response and hasattr(response, 'content') and response.content:  
                logger.info("✅ Task completed successfully!")  
                responses.append(RunResponse(  
                    event=RunEvent.workflow_completed,  
                    content=response.content,  
                ))  
            else:  
                # If response doesn't have content, try to get it as string  
                content = str(response) if response else "Task completed but no response content was generated."  
                logger.warning(f"⚠️ No standard response content, using: {content[:100]}...")  
                responses.append(RunResponse(  
                    event=RunEvent.workflow_completed,  
                    content=content,  
                ))  
                
        except Exception as e:  
            logger.error(f"❌ Error during agent execution: {str(e)}")  
            responses.append(RunResponse(  
                event=RunEvent.workflow_completed,  
                content=f"Error occurred during task execution: {str(e)}",  
            ))  
        finally:  
            # Clean up MCP stack  
            if hasattr(self, 'mcp_stack') and self.mcp_stack:  
                await self.mcp_stack.aclose()  
        
        return responses

async def run_agent_task(
    prompt: str = None, 
    agent_ids: list[int] = None, 
    host_agent_id: int = None,
    execution_mode: str = "single",
    **kwargs
) -> Dict[str, Any]:
    """
    Run agent task with dynamic configuration from database and return response.
    
    Supports both single agent and team execution modes.
    
    Args:
        prompt (str): Custom prompt for the agent task
        agent_ids (list[int]): List of agent IDs to use
        host_agent_id (int, optional): Host agent ID for team coordination
        execution_mode (str): "single" or "team"
        **kwargs: Additional parameters
        
    Returns:
        Dict[str, Any]: The result of the agent execution
    """
    try:
        # Initialize the workflow
        workflow = AgentWorkflow(
            session_id=f"agent-task-{hash(prompt or 'default')}",
        )
        
        # Initialize the team with specific agent_ids or all agents
        await workflow.initialize_team(
            agent_ids=agent_ids,
            host_agent_id=host_agent_id,
            execution_mode=execution_mode
        )
        
        # Execute the workflow and get response iterator
        workflow_result = list(workflow.run(prompt=prompt, **kwargs))
        
        # Return the last result
        if workflow_result:
            last_result = workflow_result[-1]
            logger.info(f"Workflow result: {last_result.content}")
            return {
                "status": "completed",
                "message": "Task executed successfully",
                "content": last_result.content,
                "prompt": prompt,
                "parameters": kwargs,
                "agent_ids": agent_ids,
                "host_agent_id": host_agent_id,
                "execution_mode": execution_mode
            }
        else:
            logger.warning("No workflow result found")
            return {
                "status": "error",
                "message": "No result found, please try reformulating your request",
                "content": None,
                "prompt": prompt,
                "parameters": kwargs,
                "agent_ids": agent_ids,
                "host_agent_id": host_agent_id,
                "execution_mode": execution_mode
            }
            
    except Exception as e:
        logger.error(f"❌ An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Error occurred during task execution: {str(e)}",
            "content": None,
            "prompt": prompt,
            "parameters": kwargs,
            "agent_ids": agent_ids,
            "host_agent_id": host_agent_id,
            "execution_mode": execution_mode
        }


async def run_agent_task_legacy(prompt: str = None):
    """
    Legacy function for running agent task (for backward compatibility).
    This version prints output instead of returning it.
    """
    result = await run_agent_task(prompt)
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    if result['content']:
        print(f"Content: {result['content']}")


async def main():  
    """
    Main function to run the agent task.
    """
    print("🤖 Starting agno_hub Hub Agent...")
    await run_agent_task_legacy()


if __name__ == "__main__":
    asyncio.run(main())