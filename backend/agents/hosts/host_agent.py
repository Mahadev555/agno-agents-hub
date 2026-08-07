"""
Factory for turning stored agent configurations into live Agno objects.

This module owns the config -> Agno translation only. It does not touch the
database and it does not manage execution lifecycle; see agents/subhost/agent.py.
"""

import json
import os
from typing import Any, Dict, List, Optional

from agno.agent import Agent
from agno.models.azure import AzureOpenAI
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat
from agno.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.mcp import MCPTools
from agno.utils.log import logger
from dotenv import load_dotenv

load_dotenv()

# Agno only accepts these three; anything else silently disables delegation.
VALID_TEAM_MODES = ("route", "coordinate", "collaborate")
DEFAULT_TEAM_MODE = "coordinate"

DEFAULT_MODEL_ID = "gemini-2.5-flash-lite"


class AgentBuildError(Exception):
    """Raised when a stored configuration cannot be turned into an Agno object."""


def _as_dict(config: Any, label: str) -> Dict[str, Any]:
    """Accept either a dict or a JSON string, and fail loudly on anything else."""
    if isinstance(config, dict):
        return config
    if isinstance(config, str):
        try:
            return json.loads(config)
        except json.JSONDecodeError as exc:
            raise AgentBuildError(f"{label} is not valid JSON: {exc}") from exc
    raise AgentBuildError(f"{label} must be a dict or JSON string, got {type(config).__name__}")


def _inner_config(agent_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pull the nested `config` blob out of a database row.

    Rows are stored as {name, description, is_mcp, mcp_config, config: {...}}.
    Older/hand-seeded rows sometimes flatten everything to the top level, so fall
    back to the row itself rather than raising a KeyError at execution time.
    """
    agent_row = _as_dict(agent_row, "agent_config")
    inner = agent_row.get("config")
    if not inner:
        return agent_row
    return _as_dict(inner, "agent_config['config']")


async def create_dynamic_team_with_mcp(
    team_config: Dict[str, Any],
    agent_configs: List[Dict[str, Any]],
) -> Team:
    """
    Create a Team from a host-agent config and a list of member agent rows.

    Args:
        team_config: The host agent's `config` blob (name, mode, model_config, ...)
        agent_configs: Member agent rows as stored in the database

    Returns:
        A Team whose members were built from the supplied configs.
    """
    if not agent_configs:
        raise AgentBuildError("Cannot create a team with no member agents")

    team_config = _as_dict(team_config, "team_config")
    agents = [build_agent(agent_config) for agent_config in agent_configs]

    mode = team_config.get("mode", DEFAULT_TEAM_MODE)
    if mode not in VALID_TEAM_MODES:
        logger.warning(
            f"Team mode '{mode}' is not one of {VALID_TEAM_MODES}; "
            f"falling back to '{DEFAULT_TEAM_MODE}'. "
            "An invalid mode disables task delegation entirely."
        )
        mode = DEFAULT_TEAM_MODE

    logger.info(f"Building team '{team_config.get('name', 'Dynamic Team')}' "
                f"(mode={mode}, members={[a.name for a in agents]})")

    return Team(
        name=team_config.get("name", "Dynamic Team"),
        mode=mode,
        model=_get_model_from_config(team_config.get("model_config", {})),
        members=agents,
        instructions=team_config.get("instructions", ""),
        **team_config.get("additional_params", {}),
    )


def build_agent(agent_row: Dict[str, Any]) -> Agent:
    """Build a single Agno Agent from a database row, MCP or simple."""
    agent_row = _as_dict(agent_row, "agent_config")
    if agent_row.get("is_mcp", False):
        return _create_mcp_agent(agent_row)
    return _create_simple_agent(agent_row)


def _create_mcp_agent(agent_row: Dict[str, Any]) -> Agent:
    """
    Create an MCP-backed agent.

    The MCPTools instance is returned un-entered; the caller is responsible for
    entering it into an AsyncExitStack on the same event loop that will run the
    agent. See agents/subhost/agent.py.
    """
    mcp_config = agent_row.get("mcp_config") or {}
    inner = _inner_config(agent_row)

    mcp_tools = MCPTools(
        url=mcp_config.get("url", "http://localhost:3001/sse"),
        transport=mcp_config.get("transport", "sse"),
        timeout_seconds=mcp_config.get("timeout_seconds", 300),
        **mcp_config.get("additional_params", {}),
    )

    return Agent(
        name=inner.get("name", agent_row.get("name", "MCP Agent")),
        role=inner.get("role", "Assistant"),
        model=_get_model_from_config(inner.get("model_config", {})),
        tools=[mcp_tools],
        description=inner.get("description", "MCP-enabled agent"),
        instructions=inner.get("instructions", ""),
        markdown=inner.get("markdown", True),
        show_tool_calls=inner.get("show_tool_calls", True),
        **inner.get("additional_params", {}),
    )


def _create_simple_agent(agent_row: Dict[str, Any]) -> Agent:
    """Create an agent backed by the built-in tool registry."""
    inner = _inner_config(agent_row)

    return Agent(
        name=inner.get("name", agent_row.get("name", "Simple Agent")),
        role=inner.get("role", "Assistant"),
        model=_get_model_from_config(inner.get("model_config", {})),
        tools=_get_tools_from_config(inner.get("tools", [])),
        description=inner.get("description", ""),
        instructions=inner.get("instructions", ""),
        markdown=inner.get("markdown", True),
        show_tool_calls=inner.get("show_tool_calls", True),
        **inner.get("additional_params", {}),
    )


def _get_model_from_config(model_config: Dict[str, Any]):
    """Create a model instance from configuration, defaulting to Gemini."""
    model_config = model_config or {}
    model_type = model_config.get("type", "google")
    model_id = model_config.get("id", DEFAULT_MODEL_ID)
    max_tokens = model_config.get("max_tokens")
    extra = model_config.get("additional_params", {})

    if model_type == "azure":
        return AzureOpenAI(
            id=model_id if model_id.startswith("gpt") else "gpt-4o",
            max_tokens=max_tokens or 16384,
            api_version=model_config.get("api_version") or os.getenv("AZURE_OPENAI_API_VERSION"),
            **extra,
        )

    if model_type == "openai":
        return OpenAIChat(id=model_id, max_tokens=max_tokens, **extra)

    if model_type != "google":
        logger.warning(f"Unknown model type '{model_type}'; falling back to google/{DEFAULT_MODEL_ID}")
        model_id = DEFAULT_MODEL_ID

    # Gemini names the cap max_output_tokens, not max_tokens.
    if max_tokens:
        return Gemini(id=model_id, max_output_tokens=max_tokens, **extra)
    return Gemini(id=model_id, **extra)


# Tool name -> zero-arg factory. Factories (not instances) so each agent gets a
# fresh tool object instead of sharing one across every agent in the process.
TOOL_REGISTRY = {
    "duckduckgo": DuckDuckGoTools,
}


def _get_tools_from_config(tool_names: Optional[List[str]]) -> List:
    """Map configured tool names to instances, failing loudly on unknown names."""
    if not tool_names:
        return []

    unknown = [name for name in tool_names if name not in TOOL_REGISTRY]
    if unknown:
        raise AgentBuildError(
            f"Unknown tool(s) {unknown}. Registered tools: {sorted(TOOL_REGISTRY)}"
        )

    return [TOOL_REGISTRY[name]() for name in tool_names]
