"""
Persistence for run records.

Each method opens and closes its own short transaction so a long-lived agent
execution never holds a database connection while waiting on an LLM.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from connection import session_scope
from models.base import utcnow
from models.run import Run, RunStatus

logger = logging.getLogger(__name__)


class RunService:
    """Create and update durable run records."""

    @staticmethod
    def create(
        prompt: str,
        mode: str,
        agent_ids: List[int],
        host_agent_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Insert a pending run and return it."""
        run_id = str(uuid.uuid4())
        with session_scope() as session:
            run = Run(
                run_id=run_id,
                status=RunStatus.PENDING,
                mode=mode,
                prompt=prompt,
                agent_ids=agent_ids,
                host_agent_id=host_agent_id,
            )
            session.add(run)
            session.flush()
            record = run.to_dict()

        logger.info(f"[{run_id}] run created (mode={mode}, agents={agent_ids})")
        return record

    @staticmethod
    def mark_running(run_id: str) -> None:
        """Move a run to `running` and stamp its start time."""
        with session_scope() as session:
            run = session.query(Run).filter(Run.run_id == run_id).first()
            if not run:
                logger.warning(f"[{run_id}] mark_running: run not found")
                return
            run.status = RunStatus.RUNNING
            run.started_at = utcnow()

    @staticmethod
    def finish(
        run_id: str,
        status: str,
        output: Optional[str] = None,
        error: Optional[str] = None,
        usage: Optional[Dict[str, int]] = None,
    ) -> None:
        """Write the terminal state, duration, and token usage."""
        with session_scope() as session:
            run = session.query(Run).filter(Run.run_id == run_id).first()
            if not run:
                logger.warning(f"[{run_id}] finish: run not found")
                return

            run.status = status
            run.output = output
            run.error = error
            run.finished_at = utcnow()

            started = run.started_at or run.created_at
            if started:
                delta = run.finished_at - started
                run.duration_ms = int(delta.total_seconds() * 1000)

            if usage:
                run.input_tokens = usage.get("input_tokens")
                run.output_tokens = usage.get("output_tokens")
                run.total_tokens = usage.get("total_tokens")

        logger.info(f"[{run_id}] run finished status={status}")

    @staticmethod
    def get(run_id: str) -> Optional[Dict[str, Any]]:
        """Fetch one run."""
        with session_scope() as session:
            run = session.query(Run).filter(Run.run_id == run_id).first()
            return run.to_dict() if run else None

    @staticmethod
    def list_recent(limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch recent runs, newest first."""
        with session_scope() as session:
            query = session.query(Run)
            if status:
                query = query.filter(Run.status == status)
            runs = query.order_by(Run.created_at.desc()).limit(limit).all()
            return [run.to_dict() for run in runs]

    @staticmethod
    def reap_orphans() -> int:
        """
        Fail any run still marked pending/running at startup.

        Execution happens in-process, so a run in a non-terminal state after a
        restart can never make progress. Without this they linger forever.
        """
        with session_scope() as session:
            stale = (
                session.query(Run)
                .filter(Run.status.in_([RunStatus.PENDING, RunStatus.RUNNING]))
                .all()
            )
            for run in stale:
                run.status = RunStatus.ERROR
                run.error = "Server restarted while this run was in progress"
                run.finished_at = utcnow()
            count = len(stale)

        if count:
            logger.warning(f"Reaped {count} orphaned run(s) from a previous process")
        return count
