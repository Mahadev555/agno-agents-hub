"""
Durable record of every agent/team execution.

Before this table existed a run left no trace: no history, no way to see what an
agent actually cost, no way to debug a failure after the HTTP response was gone.
Everything downstream (history UI, retries, cancellation, cost reporting) reads
from here.
"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base, utcnow


class RunStatus:
    """Terminal and non-terminal run states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"

    TERMINAL = (COMPLETED, ERROR)


class Run(Base):
    """A single execution of one agent or one team."""

    __tablename__ = "runs"

    run_id = Column(String(36), primary_key=True)  # uuid4
    status = Column(String(20), nullable=False, default=RunStatus.PENDING, index=True)
    mode = Column(String(20), nullable=False)  # "single" | "team"

    prompt = Column(Text, nullable=False)
    output = Column(Text, nullable=True)
    error = Column(Text, nullable=True)

    # Which agents took part. JSONB so a team's membership is queryable.
    agent_ids = Column(JSONB, nullable=False, default=list)
    host_agent_id = Column(Integer, nullable=True)

    # Usage, for cost attribution. Null when the provider does not report it.
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            "run_id": self.run_id,
            "status": self.status,
            "mode": self.mode,
            "prompt": self.prompt,
            "output": self.output,
            "error": self.error,
            "agent_ids": self.agent_ids or [],
            "host_agent_id": self.host_agent_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
        }

    def __repr__(self):
        return f"<Run(id={self.run_id}, status='{self.status}', mode='{self.mode}')>"
