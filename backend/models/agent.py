"""
SQLAlchemy models for agents and teams.

One `agents` table holds both workers and coordinators, discriminated by `kind`.
They were previously two tables (`agents` and `host_agent`) with ~90% identical
columns, duplicated services, duplicated controllers, and an `is_host` flag
threaded through the routes. A coordinator is an agent with a coordinating role.

Teams are their own entity. Composition used to be sent by the client on every
request, which meant a team could not be saved, shared, or versioned, and any
caller could compose arbitrary agents.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from models.base import Base, utcnow


class AgentKind:
    """What an agent is for."""

    SIMPLE = "simple"  # a worker with local tools
    MCP = "mcp"  # a worker backed by an MCP server
    HOST = "host"  # a coordinator that delegates to other agents

    ALL = (SIMPLE, MCP, HOST)
    WORKERS = (SIMPLE, MCP)


class Agent(Base):
    """An agent definition: worker or coordinator."""

    __tablename__ = "agents"

    agent_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # simple | mcp | host. Replaces the old agent_type + is_mcp + separate table.
    kind = Column(String(20), nullable=False, default=AgentKind.SIMPLE, index=True)

    is_active = Column(Boolean, default=True, index=True)

    # Ownership. Nullable so the migration can adopt pre-auth rows, but every
    # row created through the API has an owner.
    owner_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Marketplace visibility: public agents are readable (never writable) by
    # anyone signed in.
    is_public = Column(Boolean, nullable=False, default=False, index=True)

    mcp_config = Column(JSONB, nullable=True, default=dict)
    config = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime, default=utcnow, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    @property
    def is_mcp(self) -> bool:
        """Kept so existing callers and API responses keep working."""
        return self.kind == AgentKind.MCP

    @property
    def is_host(self) -> bool:
        return self.kind == AgentKind.HOST

    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "kind": self.kind,
            # agent_type/is_mcp are derived; the API contract predates `kind`.
            "agent_type": self.kind,
            "is_mcp": self.is_mcp,
            "is_active": self.is_active,
            "owner_id": self.owner_id,
            "is_public": self.is_public,
            "mcp_config": self.mcp_config,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_host_dict(self):
        """
        Shape expected by the legacy /api/host-agents responses.

        `mode` lived in its own column on host_agent; it is part of the config
        blob now, because orchestration mode is a property of how a team runs.
        """
        payload = self.to_dict()
        payload["mode"] = (self.config or {}).get("mode", "coordinate")
        return payload

    def __repr__(self):
        return f"<Agent(id={self.agent_id}, name='{self.name}', kind='{self.kind}')>"


class Team(Base):
    """
    A saved, reusable group of agents with a coordinator.

    Persisting this is what turns ad-hoc requests into something shareable and
    versionable, and gives a place to hang team-level settings later.
    """

    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # The coordinator. Restricted at the service layer to kind == host.
    host_agent_id = Column(
        Integer, ForeignKey("agents.agent_id", ondelete="RESTRICT"), nullable=False
    )

    # route | coordinate | collaborate. Belongs to the team, not the coordinator,
    # because the same host can drive different teams differently.
    mode = Column(String(20), nullable=False, default="coordinate")

    is_active = Column(Boolean, default=True, index=True)
    config = Column(JSONB, nullable=False, default=dict)

    owner_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_public = Column(Boolean, nullable=False, default=False, index=True)

    created_at = Column(DateTime, default=utcnow, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    host_agent = relationship("Agent", foreign_keys=[host_agent_id])
    members = relationship(
        "TeamMember",
        back_populates="team",
        cascade="all, delete-orphan",
        order_by="TeamMember.position",
    )

    def to_dict(self, include_members=True):
        """Convert model instance to dictionary."""
        payload = {
            "team_id": self.team_id,
            "name": self.name,
            "description": self.description,
            "host_agent_id": self.host_agent_id,
            "mode": self.mode,
            "is_active": self.is_active,
            "owner_id": self.owner_id,
            "is_public": self.is_public,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_members:
            payload["members"] = [m.to_dict() for m in self.members]
        return payload

    def __repr__(self):
        return f"<Team(id={self.team_id}, name='{self.name}', mode='{self.mode}')>"


class TeamMember(Base):
    """
    Membership of an agent in a team.

    `position` is meaningful for sequential-style orchestration and determines
    the order members are presented to the coordinator.
    """

    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "agent_id", name="uq_team_agent"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(
        Integer, ForeignKey("teams.team_id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id = Column(
        Integer, ForeignKey("agents.agent_id", ondelete="CASCADE"), nullable=False, index=True
    )
    position = Column(Integer, nullable=False, default=0)

    team = relationship("Team", back_populates="members")
    agent = relationship("Agent", foreign_keys=[agent_id])

    def to_dict(self):
        return {
            "agent_id": self.agent_id,
            "position": self.position,
            "name": self.agent.name if self.agent else None,
            "kind": self.agent.kind if self.agent else None,
        }

    def __repr__(self):
        return f"<TeamMember(team={self.team_id}, agent={self.agent_id})>"


# The old model exposed HostAgent as a separate class. Coordinators are now rows
# in `agents` with kind='host'; this alias keeps stale imports from crashing.
HostAgent = Agent
