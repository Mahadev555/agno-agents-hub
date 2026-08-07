"""
Run Controller

Owns the lifecycle of a run: create the record, execute in the background,
publish events to subscribers, and write the terminal state.

Execution is deliberately decoupled from the HTTP request that started it, so a
client disconnect (closed tab, dropped wifi, proxy timeout) no longer aborts a
run halfway through and loses the work.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from agents.subhost.agent import stream_agent_task
from controllers.agent_execution_controller import AgentExecutionController
from models.run import RunStatus
from services.run_bus import run_bus
from services.run_service import RunService

logger = logging.getLogger(__name__)

# Strong references to in-flight tasks. asyncio only holds weak references, so
# without this a run can be garbage collected mid-execution.
_active_tasks: set = set()


class RunController:
    """Create and drive runs."""

    @staticmethod
    def start(
        prompt: str,
        agent_ids: Optional[List[int]] = None,
        host_agent_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Validate the request, persist a pending run, and schedule execution.

        Returns immediately with the run record; the caller subscribes to
        /api/runs/{run_id}/events for progress.
        """
        prompt = (prompt or "").strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")

        # Resolve configs up front so a bad agent id is a synchronous 404
        # instead of an error the client only discovers over the event stream.
        agents = AgentExecutionController._load_agents(agent_ids)
        mode = "single" if (len(agents) == 1 and host_agent_id is None) else "team"

        host_config = None
        if mode == "team":
            if host_agent_id is None:
                host_agent = AgentExecutionController._default_host_agent()
                host_agent_id = host_agent["agent_id"]
            host_config = AgentExecutionController._load_host_config(host_agent_id)

        record = RunService.create(
            prompt=prompt,
            mode=mode,
            agent_ids=[a["agent_id"] for a in agents],
            host_agent_id=host_agent_id if mode == "team" else None,
        )
        run_id = record["run_id"]

        # Open the channel before scheduling so a fast subscriber cannot miss
        # the beginning of the stream.
        run_bus.open(run_id)

        task = asyncio.create_task(
            RunController._execute(
                run_id=run_id,
                prompt=prompt,
                agent_configs=agents,
                host_config=host_config,
                execution_mode=mode,
            )
        )
        _active_tasks.add(task)
        task.add_done_callback(_active_tasks.discard)

        return record

    @staticmethod
    async def _execute(
        run_id: str,
        prompt: str,
        agent_configs: List[Dict[str, Any]],
        host_config: Optional[Dict[str, Any]],
        execution_mode: str,
    ) -> None:
        """Drive the run to a terminal state, publishing events as it goes."""
        channel = run_bus.open(run_id)
        RunService.mark_running(run_id)

        output = ""
        error: Optional[str] = None
        usage: Optional[Dict[str, Any]] = None

        try:
            async for event in stream_agent_task(
                prompt=prompt,
                agent_configs=agent_configs,
                host_config=host_config,
                execution_mode=execution_mode,
                session_id=run_id,
            ):
                channel.publish(event)

                if event["type"] == "completed":
                    output = event.get("output", "")
                    usage = event.get("usage")
                elif event["type"] == "error":
                    error = event.get("message", "Unknown error")

        except asyncio.CancelledError:
            error = "Run was cancelled"
            channel.publish({"type": "error", "message": error})
            raise
        except Exception as exc:
            # The generator handles its own failures; this is a last resort so a
            # run can never be left stuck in `running`.
            error = f"Unexpected error: {exc}"
            logger.error(f"[{run_id}] {error}", exc_info=True)
            channel.publish({"type": "error", "message": error})
        finally:
            status = RunStatus.ERROR if error else RunStatus.COMPLETED
            RunService.finish(
                run_id=run_id,
                status=status,
                output=output or None,
                error=error,
                usage=usage,
            )
            channel.close()

    @staticmethod
    def get(run_id: str) -> Dict[str, Any]:
        """Fetch a run record, 404ing if unknown."""
        record = RunService.get(run_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return record

    @staticmethod
    def list_recent(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List recent runs, newest first."""
        return RunService.list_recent(limit=limit, status=status)
