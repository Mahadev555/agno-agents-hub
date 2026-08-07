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
from typing import Any, AsyncIterator, Dict, List, Optional

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


async def _build_runnable(
    prompt: str,
    agent_configs: List[Dict[str, Any]],
    host_config: Optional[Dict[str, Any]],
    execution_mode: str,
    session_id: str,
):
    """
    Validate the request and construct the Agent or Team that will run it.

    Shared by the streaming and non-streaming paths so the two cannot drift
    apart in how they interpret a configuration.

    Returns:
        (runnable, members) where runnable is an Agent or Team and members is
        the list of Agents whose MCP sessions need managing.

    Raises:
        AgentExecutionError: for any setup problem.
    """
    if not prompt:
        raise AgentExecutionError("Prompt cannot be empty")

    if execution_mode not in ("single", "team"):
        raise AgentExecutionError(
            f"Unknown execution_mode '{execution_mode}'; expected 'single' or 'team'"
        )

    if not agent_configs:
        raise AgentExecutionError("No agent configurations supplied")

    try:
        if execution_mode == "single":
            if len(agent_configs) != 1:
                raise AgentExecutionError(
                    f"Single mode expects exactly 1 agent, got {len(agent_configs)}"
                )
            agent = build_agent(agent_configs[0])
            logger.info(f"[{session_id}] Running single agent '{agent.name}'")
            return agent, [agent]

        if not host_config:
            raise AgentExecutionError("Team mode requires a host agent configuration")
        team = await create_dynamic_team_with_mcp(host_config, agent_configs)
        members = list(team.members)
        logger.info(
            f"[{session_id}] Running team '{team.name}' with {len(members)} member(s)"
        )
        return team, members
    except AgentBuildError as exc:
        raise AgentExecutionError(str(exc)) from exc


def extract_usage(response: Any) -> Dict[str, Optional[int]]:
    """
    Pull token counts out of an Agno response.

    Agno reports metrics as per-message lists (e.g. input_tokens: [12, 40]), so
    sum them. Providers that report nothing yield None rather than a false zero.
    """
    metrics = getattr(response, "metrics", None)
    if not isinstance(metrics, dict):
        return {"input_tokens": None, "output_tokens": None, "total_tokens": None}

    def total(key: str) -> Optional[int]:
        value = metrics.get(key)
        if isinstance(value, list):
            numbers = [v for v in value if isinstance(v, (int, float))]
            return int(sum(numbers)) if numbers else None
        if isinstance(value, (int, float)):
            return int(value)
        return None

    usage = {
        "input_tokens": total("input_tokens"),
        "output_tokens": total("output_tokens"),
        "total_tokens": total("total_tokens"),
    }
    if usage["total_tokens"] is None and (usage["input_tokens"] or usage["output_tokens"]):
        usage["total_tokens"] = (usage["input_tokens"] or 0) + (usage["output_tokens"] or 0)
    return usage


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
    session_id = session_id or f"run-{uuid.uuid4()}"
    prompt = (prompt or "").strip()
    runnable, members = await _build_runnable(
        prompt, agent_configs, host_config, execution_mode, session_id
    )

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
    if execution_mode == "team":
        result["host_agent_name"] = runnable.name

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
            usage=extract_usage(response),
        )
        return result


async def stream_agent_task(
    prompt: str,
    agent_configs: List[Dict[str, Any]],
    host_config: Optional[Dict[str, Any]] = None,
    execution_mode: str = "single",
    session_id: Optional[str] = None,
    **kwargs,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Execute a task, yielding normalized events as they happen.

    Event shape is deliberately provider-agnostic so the API contract does not
    change if Agno renames its own events:

        {"type": "started",   "agents": [...], "mode": "team"}
        {"type": "token",     "text": "..."}                  incremental output
        {"type": "tool_call", "name": "duckduckgo_search", "status": "started"}
        {"type": "completed", "output": "...", "usage": {...}}
        {"type": "error",     "message": "..."}

    A terminal event ("completed" or "error") is always the last thing yielded,
    including when setup fails, so a consumer never has to infer the end.
    """
    session_id = session_id or f"run-{uuid.uuid4()}"
    prompt = (prompt or "").strip()

    try:
        runnable, members = await _build_runnable(
            prompt, agent_configs, host_config, execution_mode, session_id
        )
    except AgentExecutionError as exc:
        yield {"type": "error", "message": str(exc)}
        return

    yield {
        "type": "started",
        "mode": execution_mode,
        "name": runnable.name,
        "agents": [getattr(m, "name", "?") for m in members],
    }

    collected: List[str] = []
    final_response: Any = None

    async with AsyncExitStack() as stack:
        try:
            await _register_mcp_sessions(stack, members)
        except BaseException as exc:
            detail = _describe_exception(exc)
            logger.error(f"[{session_id}] MCP connection failed: {detail}")
            yield {
                "type": "error",
                "message": (
                    f"Could not connect to an MCP server for this agent ({detail}). "
                    "Check that the MCP endpoint in the agent's mcp_config is running."
                ),
            }
            return

        try:
            # arun(stream=True) returns a coroutine yielding the async iterator.
            stream_kwargs = dict(kwargs)
            if isinstance(runnable, Team):
                stream_kwargs.setdefault("stream_intermediate_steps", True)

            iterator = await runnable.arun(
                prompt, stream=True, session_id=session_id, **stream_kwargs
            )

            async for event in iterator:
                final_response = event
                kind = str(getattr(event, "event", "") or "")
                content = getattr(event, "content", None)

                if kind == "ToolCallStarted":
                    yield {
                        "type": "tool_call",
                        "status": "started",
                        "name": _tool_name(event),
                    }
                elif kind == "ToolCallCompleted":
                    yield {
                        "type": "tool_call",
                        "status": "completed",
                        "name": _tool_name(event),
                    }
                elif kind == "RunResponse" and isinstance(content, str) and content:
                    collected.append(content)
                    yield {"type": "token", "text": content}
                elif kind == "RunError":
                    yield {"type": "error", "message": str(content or "Run failed")}
                    return

        except BaseException as exc:
            detail = _describe_exception(exc)
            logger.error(f"[{session_id}] Execution failed: {detail}")
            yield {"type": "error", "message": f"Execution failed: {detail}"}
            return

    output = "".join(collected).strip()
    if not output:
        yield {"type": "error", "message": "Agent returned an empty response"}
        return

    logger.info(f"[{session_id}] Completed ({len(output)} chars)")
    yield {
        "type": "completed",
        "output": output,
        "usage": extract_usage(final_response),
    }


def _tool_name(event: Any) -> str:
    """Best-effort tool name from a tool-call event."""
    tool = getattr(event, "tool", None)
    for attr in ("tool_name", "name"):
        value = getattr(tool, attr, None)
        if value:
            return str(value)
    tools = getattr(event, "tools", None)
    if isinstance(tools, list) and tools:
        first = tools[0]
        if isinstance(first, dict):
            return str(first.get("tool_name") or first.get("name") or "tool")
    return "tool"
