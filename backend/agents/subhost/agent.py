"""
Async execution runtime for agents and teams.

Two execution paths:

  single -> build one Agent and await agent.arun(prompt)
  team   -> build a Team from a host agent config and await team.arun(prompt)

Everything is async end-to-end on the caller's event loop. MCP tool sessions are
entered into an AsyncExitStack inside the same coroutine that runs the agent, so
sessions are always created and closed on the loop that uses them.

Callers pass already-loaded configuration dicts; this module does not query the
database.
"""

import uuid
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from agno.agent import Agent
from agno.team import Team
from agno.tools.mcp import MCPTools
from agno.utils.log import logger

from agents.hosts.host_agent import (
    AgentBuildError,
    build_agent,
    create_dynamic_team_with_mcp,
)


class AgentExecutionError(Exception):
    """Raised when a task cannot be set up or executed."""


class MCPConnectionError(AgentExecutionError):
    """Raised when an agent's configured MCP server is unreachable."""


async def _register_mcp_sessions(stack: AsyncExitStack, agents: List[Agent]) -> None:
    """Enter every MCPTools instance on the current event loop."""
    for agent in agents:
        for tool in getattr(agent, "tools", None) or []:
            if isinstance(tool, MCPTools):
                logger.info(f"Opening MCP session for agent '{agent.name}'")
                await stack.enter_async_context(tool)


def _describe_exception(exc: BaseException) -> str:
    """
    Flatten an exception into a readable message.

    anyio task groups (used by the MCP client) wrap real failures in an
    ExceptionGroup, whose own str() is the useless "unhandled errors in a
    TaskGroup (1 sub-exception)". Unwrap so the caller sees the actual cause.
    """
    if isinstance(exc, BaseExceptionGroup):
        return "; ".join(_describe_exception(sub) for sub in exc.exceptions)
    cause = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
    return cause


def _extract_content(response: Any) -> str:
    """Pull text content out of an Agno RunResponse."""
    if response is None:
        return ""
    content = getattr(response, "content", None)
    if content is None:
        return str(response)
    if isinstance(content, str):
        return content
    return str(content)


async def run_agent_task(
    prompt: str,
    agent_configs: List[Dict[str, Any]],
    host_config: Optional[Dict[str, Any]] = None,
    execution_mode: str = "single",
    session_id: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Execute a task against one agent or a coordinated team.

    Args:
        prompt: The task to run.
        agent_configs: Agent rows already loaded from the database.
        host_config: The host agent's `config` blob. Required for team mode.
        execution_mode: "single" or "team".
        session_id: Stable session id; generated if not supplied.
        **kwargs: Passed through to Agno's arun().

    Returns:
        Dict with status ("completed" | "error"), content, and run metadata.

    Raises:
        AgentExecutionError: If the request cannot be set up (bad mode, missing
            configs, unbuildable agent). Setup problems raise instead of silently
            substituting a different set of agents.
    """
    if not prompt or not prompt.strip():
        raise AgentExecutionError("Prompt cannot be empty")

    if execution_mode not in ("single", "team"):
        raise AgentExecutionError(
            f"Unknown execution_mode '{execution_mode}'; expected 'single' or 'team'"
        )

    if not agent_configs:
        raise AgentExecutionError("No agent configurations supplied")

    session_id = session_id or f"run-{uuid.uuid4()}"
    prompt = prompt.strip()

    result: Dict[str, Any] = {
        "status": "error",
        "message": "",
        "content": None,
        "prompt": prompt,
        "parameters": kwargs,
        "agent_ids": [c.get("agent_id") for c in agent_configs],
        "execution_mode": execution_mode,
        "session_id": session_id,
    }

    # Build phase. Failures here are configuration errors and must surface.
    try:
        if execution_mode == "single":
            if len(agent_configs) != 1:
                raise AgentExecutionError(
                    f"Single mode expects exactly 1 agent, got {len(agent_configs)}"
                )
            runnable = build_agent(agent_configs[0])
            members = [runnable]
            logger.info(f"[{session_id}] Running single agent '{runnable.name}'")
        else:
            if not host_config:
                raise AgentExecutionError("Team mode requires a host agent configuration")
            runnable = await create_dynamic_team_with_mcp(host_config, agent_configs)
            members = list(runnable.members)
            result["host_agent_name"] = runnable.name
            logger.info(
                f"[{session_id}] Running team '{runnable.name}' "
                f"with {len(members)} member(s)"
            )
    except AgentBuildError as exc:
        raise AgentExecutionError(str(exc)) from exc

    # Execution phase. MCP sessions live and die inside this block, on this loop.
    async with AsyncExitStack() as stack:
        try:
            await _register_mcp_sessions(stack, members)
        except BaseException as exc:
            detail = _describe_exception(exc)
            logger.error(f"[{session_id}] MCP connection failed: {detail}", exc_info=True)
            raise MCPConnectionError(
                f"Could not connect to an MCP server for this agent ({detail}). "
                "Check that the MCP endpoint in the agent's mcp_config is running."
            ) from exc

        try:
            response = await runnable.arun(prompt, session_id=session_id, **kwargs)
        except BaseException as exc:
            detail = _describe_exception(exc)
            logger.error(f"[{session_id}] Execution failed: {detail}", exc_info=True)
            result["message"] = f"Execution failed: {detail}"
            return result

        content = _extract_content(response)
        if not content:
            result["message"] = "Agent returned an empty response"
            return result

        logger.info(f"[{session_id}] Completed ({len(content)} chars)")
        result.update(
            status="completed",
            message="Task executed successfully",
            content=content,
        )
        return result
