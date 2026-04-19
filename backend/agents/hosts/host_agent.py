import asyncio  
import os  
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union  
from agno.agent import Agent  
from agno.models.azure import AzureOpenAI  
from agno.models.openai import OpenAIChat  
from agno.team import Team  
from agno.tools.mcp import MCPTools  
from agno.tools.duckduckgo import DuckDuckGoTools  
from dotenv import load_dotenv  
from agno.models.google import Gemini

load_dotenv()  
async def create_dynamic_team_with_mcp(  
    team_config: Dict[str, Any],  
    agent_configs: List[Dict[str, Any]]  
) -> Team:  
    """  
    Create a team with dynamically generated agents supporting both MCP and simple agents.  
      
    Args:  
        team_config: Configuration for the team (name, mode, model, etc.)  
        agent_configs: Agent configurations - can be dict from DB or list format  
      
    Returns:  
        Team instance with dynamically created agents  
    """  
    agents = []  
    mcp_tools_instances = []  # Keep track of MCP tools for proper cleanup  
      
    for agent_config in agent_configs:  
        is_mcp = agent_config.get("is_mcp", False)  
          
        if is_mcp:  
            # Create MCP agent similar to your HR agent example  
            agent = await _create_mcp_agent(agent_config, mcp_tools_instances)  
        else:  
            # Create simple agent with regular tools  
            agent = _create_simple_agent(agent_config)  
          
        agents.append(agent)  
        
    print(f":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::==>> agents: {agents}")
      
    # Create team with dynamic agents  
    team = Team(  
        name=team_config.get("name", "Dynamic Team"),  
        mode=team_config.get("mode", "coordinate"),  
        model=_get_model_from_config(team_config.get("model_config", {})),  
        members=agents,  
        instructions=team_config.get("instructions", ""),  
        **team_config.get("additional_params", {})  
    )  
      
    return team

  
async def _create_mcp_agent(agent_config: Dict[str, Any], mcp_tools_instances: List) -> Agent:  
    """Create an MCP agent using the pattern from your HR agent example."""  
    # Convert string config to dict if needed
    if isinstance(agent_config, str):
        try:
            agent_config = json.loads(agent_config)
        except json.JSONDecodeError:
            raise ValueError("agent_config is not valid JSON")
    
    mcp_config = agent_config.get("mcp_config", {})  
      
    mcp_tools = MCPTools(  
        url=mcp_config.get("url", "http://localhost:3001/sse"),  
        transport=mcp_config.get("transport", "sse"),
        timeout_seconds=300,
        **mcp_config.get("additional_params", {})  
    )
    
    # Store the tools instance for cleanup later
    mcp_tools_instances.append(mcp_tools)

    agent_final_config = agent_config['config']

    model_config = agent_final_config['model_config']

    agent = Agent(  
        name=agent_final_config.get("name", "MCP Agent"),  
        model=_get_model_from_config(model_config),  
        tools=[mcp_tools],  
        description=agent_final_config.get("description", "MCP-enabled agent"),  
        instructions=agent_final_config.get("instructions", ""),  
        markdown=agent_final_config.get("markdown", True),  
        show_tool_calls=agent_final_config.get("show_tool_calls", True),  
        **agent_final_config.get("additional_params", {})  
    )  
    
    return agent  
  
def _create_simple_agent(agent_config: Dict[str, Any]) -> Agent:  
    """Create a simple agent with regular tools."""  
    # Convert string config to dict if needed
    if isinstance(agent_config, str):
        try:
            agent_config = json.loads(agent_config)
        except json.JSONDecodeError:
            raise ValueError("agent_config is not valid JSON")
    model_config = agent_config.get("model_config", {})
    agent_final_config = agent_config['config']

    model_config = agent_final_config['model_config']
    agent = Agent(  
        name=agent_final_config.get("name", "Simple Agent"),  
        role=agent_final_config.get("role", "Assistant"),  
        model=_get_model_from_config(model_config),  
        tools=_get_tools_from_config(agent_final_config.get("tools", [])),  
        instructions=agent_final_config.get("instructions", ""),  
        **agent_final_config.get("additional_params", {})  
    )  
    return agent
  
def _get_model_from_config(model_config: Dict[str, Any]):  
    """Create model instance from configuration.
    
    Uses gemini-2.5-flash-lite as default for all agents unless explicitly configured otherwise.
    """  
    model_type = model_config.get("type", "google")  
    model_id = model_config.get("id", "gemini-2.5-flash-lite")
      
    if model_type == "azure":  
        return AzureOpenAI(  
            id=model_id if model_id.startswith("gpt") else "gpt-4o",  
            max_tokens=model_config.get("max_tokens", 16384),  
            api_version=model_config.get("api_version") or os.getenv("AZURE_OPENAI_API_VERSION"),  
            **model_config.get("additional_params", {})  
        )  
    else:
        # Default to gemini-2.5-flash-lite for all Google models
        return Gemini(id=model_id)
  
def _get_tools_from_config(tool_names: List[str]) -> List:  
    """Map tool names to actual tool instances for simple agents."""  
    tool_mapping = {  
        "duckduckgo": DuckDuckGoTools()
    }  
    return [tool_mapping[name] for name in tool_names if name in tool_mapping]

