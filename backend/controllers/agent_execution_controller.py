"""
Agent Execution Controller

Loads agent configurations from the database and hands them to the async
execution runtime. This is the only layer that fetches execution configs, so a
request loads each agent exactly once.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from agents.subhost.agent import (
    AgentExecutionError,
    MCPConnectionError,
    run_agent_task,
)
from models.run import RunStatus
from services.database_service import DatabaseService
from services.run_service import RunService

logger = logging.getLogger(__name__)


def _to_http_error(exc: AgentExecutionError) -> HTTPException:
    """Map a setup failure to a status code that reflects whose fault it is."""
    if isinstance(exc, MCPConnectionError):
        # An unreachable upstream is not the caller's mistake.
        return HTTPException(status_code=502, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


async def _recorded(
    prompt: str,
    mode: str,
    agent_ids: List[int],
    host_agent_id: Optional[int],
    coro_factory,
    owner_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run a non-streaming execution while persisting a run record around it.

    The blocking endpoints predate /api/runs but still belong in history, so
    they write the same rows. The run id is threaded through as the session id
    so logs from both paths correlate the same way.
    """
    record = RunService.create(
        prompt=prompt,
        mode=mode,
        agent_ids=agent_ids,
        host_agent_id=host_agent_id,
        owner_id=owner_id,
    )
    run_id = record["run_id"]
    RunService.mark_running(run_id)

    try:
        result = await coro_factory(run_id)
    except HTTPException as exc:
        RunService.finish(run_id, RunStatus.ERROR, error=str(exc.detail))
        raise
    except Exception as exc:
        RunService.finish(run_id, RunStatus.ERROR, error=str(exc))
        raise

    completed = result.get("status") == "completed"
    RunService.finish(
        run_id,
        RunStatus.COMPLETED if completed else RunStatus.ERROR,
        output=result.get("content"),
        error=None if completed else result.get("message"),
        usage=result.get("usage"),
    )
    result["run_id"] = run_id
    return result


class AgentExecutionController:
    """Controller for executing agent tasks."""

    @staticmethod
    def _load_agents(agent_ids: Optional[List[int]]) -> List[Dict[str, Any]]:
        """
        Load agent rows for the given IDs in one query.

        Passing None loads every active agent. Any ID that does not resolve is a
        404 rather than a silent omission.
        """
        if agent_ids is None:
            agents = DatabaseService.get_active_agents()
            if not agents:
                raise HTTPException(status_code=400, detail="No active agents available")
            return agents

        agents = DatabaseService.get_agents_by_ids(agent_ids)
        found = {a["agent_id"] for a in agents}
        missing = [i for i in agent_ids if i not in found]
        if missing:
            raise HTTPException(status_code=404, detail=f"Agent IDs not found: {missing}")
        return agents

    @staticmethod
    def _default_host_agent() -> Dict[str, Any]:
        """
        The coordinator used when several agents are requested without one.

        Multiple agents cannot run without something to delegate between them,
        so a missing default is a hard error rather than an arbitrary pick.
        """
        host_agent = DatabaseService.get_host_agent_by_name("Mixed Agent Team")
        if not host_agent:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Multiple agents require a coordinator, but no hostAgentId was "
                    "supplied and the default 'Mixed Agent Team' host agent does "
                    "not exist."
                ),
            )
        return host_agent

    @staticmethod
    def _load_host_config(host_agent_id: int) -> Dict[str, Any]:
        """Load a host agent's config blob, 404ing if it does not exist."""
        host_agent = DatabaseService.get_host_agent_by_id(host_agent_id)
        if not host_agent:
            raise HTTPException(
                status_code=404, detail=f"Host agent with ID {host_agent_id} not found"
            )

        config = host_agent.get("config") or {}
        # The row-level mode column is authoritative if the blob omits it.
        config.setdefault("mode", host_agent.get("mode", "coordinate"))
        config.setdefault("name", host_agent.get("name", "Dynamic Team"))
        return config

    @staticmethod
    async def execute_single_agent(
        prompt: str, agent_id: int, owner_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute one agent directly, with no team wrapper."""
        agents = AgentExecutionController._load_agents([agent_id])

        async def _run(run_id: str) -> Dict[str, Any]:
            try:
                return await run_agent_task(
                    prompt=prompt,
                    agent_configs=agents,
                    execution_mode="single",
                    session_id=run_id,
                )
            except AgentExecutionError as e:
                logger.error(f"[{run_id}] single agent setup failed: {e}")
                raise _to_http_error(e)

        return await _recorded(
            prompt=prompt,
            mode="single",
            agent_ids=[agent_id],
            host_agent_id=None,
            coro_factory=_run,
            owner_id=owner_id,
        )

    @staticmethod
    async def execute_team(
        prompt: str,
        host_agent_id: int,
        member_agent_ids: List[int],
        owner_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a team coordinated by a host agent."""
        host_config = AgentExecutionController._load_host_config(host_agent_id)
        agents = AgentExecutionController._load_agents(member_agent_ids)

        async def _run(run_id: str) -> Dict[str, Any]:
            try:
                return await run_agent_task(
                    prompt=prompt,
                    agent_configs=agents,
                    host_config=host_config,
                    execution_mode="team",
                    session_id=run_id,
                )
            except AgentExecutionError as e:
                logger.error(f"[{run_id}] team setup failed: {e}")
                raise _to_http_error(e)

        result = await _recorded(
            prompt=prompt,
            mode="team",
            agent_ids=member_agent_ids,
            host_agent_id=host_agent_id,
            coro_factory=_run,
            owner_id=owner_id,
        )
        result["host_agent_id"] = host_agent_id
        return result

    @staticmethod
    async def execute_agent_task(
        prompt: str,
        agent_ids: Optional[List[int]] = None,
        host_agent_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Backing implementation for /api/chat.

        Picks a mode from the request shape: a single agent runs directly, and
        anything else is coordinated by a host agent.
        """
        agents = AgentExecutionController._load_agents(agent_ids)

        if len(agents) == 1 and host_agent_id is None:
            return await AgentExecutionController.execute_single_agent(
                prompt=prompt, agent_id=agents[0]["agent_id"], owner_id=owner_id
            )

        if host_agent_id is None:
            host_agent_id = AgentExecutionController._default_host_agent()["agent_id"]

        return await AgentExecutionController.execute_team(
            prompt=prompt,
            host_agent_id=host_agent_id,
            member_agent_ids=[a["agent_id"] for a in agents],
            owner_id=owner_id,
        )
