"""
Agent and Team write operations.

Configurations are validated through the typed schema before they are stored, so
a bad tool name or unknown model provider is rejected when an agent is saved
rather than when someone runs it.
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from connection import session_scope
from models.agent import Agent, AgentKind, Team, TeamMember
from schemas.agent_config import parse_agent_config, parse_team_config

logger = logging.getLogger(__name__)


class ConfigError(ValueError):
    """Raised when a supplied configuration is invalid."""


def _readable(exc: ValidationError) -> str:
    """Flatten a pydantic error into one line suitable for an API message."""
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"] if p != "__root__")
        parts.append(f"{loc}: {err['msg']}" if loc else err["msg"])
    return "; ".join(parts)


class AgentService:
    """Create, update, and delete agents (workers and coordinators)."""

    @staticmethod
    def create_agent(
        name: str,
        config: Dict[str, Any],
        kind: str = AgentKind.SIMPLE,
        description: str = None,
        mcp_config: Dict[str, Any] = None,
        owner_id: int = None,
        is_public: bool = False,
        **legacy,
    ) -> Dict[str, Any]:
        """
        Create an agent.

        Args:
            name: Unique name
            config: Configuration blob; validated against AgentConfig/TeamConfig
            kind: simple | mcp | host
            description: Human-readable description
            mcp_config: Connection settings for MCP agents

        Raises:
            ConfigError: if the name is taken or the config is invalid
        """
        # Older callers pass agent_type/is_mcp; map them onto `kind`.
        kind = _resolve_kind(kind, legacy)

        if kind not in AgentKind.ALL:
            raise ConfigError(f"Unknown agent kind '{kind}'. Expected one of {AgentKind.ALL}")

        try:
            if kind == AgentKind.HOST:
                validated = parse_team_config(config, name).to_storage()
            else:
                validated = parse_agent_config(config, name, description).to_storage()
        except ValidationError as exc:
            raise ConfigError(f"Invalid config: {_readable(exc)}") from exc

        with session_scope() as session:
            if session.query(Agent).filter(Agent.name == name).first():
                raise ConfigError(f"Agent with name '{name}' already exists")

            agent = Agent(
                name=name,
                description=description,
                kind=kind,
                mcp_config=mcp_config or {},
                config=validated,
                is_active=True,
                owner_id=owner_id,
                is_public=bool(is_public),
            )
            session.add(agent)
            session.flush()
            record = agent.to_dict()

        logger.info(f"Created agent: {name} (id={record['agent_id']}, kind={kind})")
        return record

    @staticmethod
    def update_agent(
        agent_id: int,
        name: str = None,
        description: str = None,
        config: Dict[str, Any] = None,
        mcp_config: Dict[str, Any] = None,
        is_active: bool = None,
        is_public: bool = None,
        **_,
    ) -> Dict[str, Any]:
        """Update an agent, revalidating the config if one is supplied."""
        with session_scope() as session:
            agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
            if not agent:
                raise ConfigError(f"Agent with ID {agent_id} not found")

            if name is not None:
                taken = (
                    session.query(Agent)
                    .filter(Agent.name == name, Agent.agent_id != agent_id)
                    .first()
                )
                if taken:
                    raise ConfigError(f"Agent name '{name}' already taken")
                agent.name = name

            if description is not None:
                agent.description = description

            if config is not None:
                try:
                    if agent.kind == AgentKind.HOST:
                        agent.config = parse_team_config(config, agent.name).to_storage()
                    else:
                        agent.config = parse_agent_config(
                            config, agent.name, agent.description
                        ).to_storage()
                except ValidationError as exc:
                    raise ConfigError(f"Invalid config: {_readable(exc)}") from exc

            if mcp_config is not None:
                agent.mcp_config = mcp_config
            if is_active is not None:
                agent.is_active = is_active
            if is_public is not None:
                agent.is_public = bool(is_public)

            session.flush()
            record = agent.to_dict()

        logger.info(f"Updated agent id={agent_id}")
        return record

    @staticmethod
    def create_host_agent(
        name: str,
        config: Dict[str, Any],
        description: str = None,
        mode: str = "coordinate",
        owner_id: int = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        """Create a coordinator. Thin wrapper kept for existing callers."""
        blob = dict(config or {})
        blob.setdefault("mode", mode)
        return AgentService.create_agent(
            name=name,
            config=blob,
            kind=AgentKind.HOST,
            description=description,
            owner_id=owner_id,
            is_public=is_public,
        )

    @staticmethod
    def delete_agent(agent_id: int) -> bool:
        """
        Delete an agent.

        Refuses if the agent coordinates a team, because the team would be left
        without a coordinator (the FK is ON DELETE RESTRICT).
        """
        with session_scope() as session:
            agent = session.query(Agent).filter(Agent.agent_id == agent_id).first()
            if not agent:
                logger.warning(f"Agent with ID {agent_id} not found")
                return False

            teams = session.query(Team).filter(Team.host_agent_id == agent_id).all()
            if teams:
                names = ", ".join(t.name for t in teams)
                raise ConfigError(
                    f"Agent {agent_id} coordinates team(s): {names}. "
                    "Delete or reassign those teams first."
                )

            session.delete(agent)

        logger.info(f"Deleted agent id={agent_id}")
        return True


def _resolve_kind(kind: str, legacy: Dict[str, Any]) -> str:
    """Map the retired agent_type/is_mcp pair onto `kind`."""
    if legacy.get("is_mcp") is True:
        return AgentKind.MCP
    agent_type = legacy.get("agent_type")
    if agent_type in AgentKind.ALL:
        return agent_type
    return kind


class TeamService:
    """Create, update, and delete saved teams."""

    @staticmethod
    def create_team(
        name: str,
        host_agent_id: int,
        member_agent_ids: List[int],
        description: str = None,
        mode: str = "coordinate",
        config: Dict[str, Any] = None,
        owner_id: int = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a team.

        Validates that the coordinator is a host agent and that every member
        exists, so an unrunnable team cannot be saved.
        """
        if mode not in ("route", "coordinate", "collaborate"):
            raise ConfigError(
                f"Unknown mode '{mode}'. Expected route, coordinate, or collaborate"
            )
        if not member_agent_ids:
            raise ConfigError("A team needs at least one member agent")

        with session_scope() as session:
            if session.query(Team).filter(Team.name == name).first():
                raise ConfigError(f"Team with name '{name}' already exists")

            host = session.query(Agent).filter(Agent.agent_id == host_agent_id).first()
            if not host:
                raise ConfigError(f"Host agent {host_agent_id} not found")
            if host.kind != AgentKind.HOST:
                raise ConfigError(
                    f"Agent {host_agent_id} ('{host.name}') is kind='{host.kind}'; "
                    "a team coordinator must be kind='host'"
                )

            found = {
                a.agent_id
                for a in session.query(Agent)
                .filter(Agent.agent_id.in_(member_agent_ids))
                .all()
            }
            missing = [i for i in member_agent_ids if i not in found]
            if missing:
                raise ConfigError(f"Member agent(s) not found: {missing}")

            team = Team(
                name=name,
                description=description,
                host_agent_id=host_agent_id,
                mode=mode,
                config=config or {},
                is_active=True,
                owner_id=owner_id,
                is_public=bool(is_public),
            )
            session.add(team)
            session.flush()

            for position, agent_id in enumerate(dict.fromkeys(member_agent_ids)):
                session.add(
                    TeamMember(team_id=team.team_id, agent_id=agent_id, position=position)
                )

            session.flush()
            session.refresh(team)
            record = team.to_dict()

        logger.info(f"Created team: {name} (id={record['team_id']})")
        return record

    @staticmethod
    def update_team(
        team_id: int,
        name: str = None,
        description: str = None,
        mode: str = None,
        member_agent_ids: List[int] = None,
        host_agent_id: int = None,
        is_active: bool = None,
    ) -> Dict[str, Any]:
        """Update a team, replacing membership wholesale when supplied."""
        with session_scope() as session:
            team = session.query(Team).filter(Team.team_id == team_id).first()
            if not team:
                raise ConfigError(f"Team {team_id} not found")

            if name is not None:
                taken = (
                    session.query(Team)
                    .filter(Team.name == name, Team.team_id != team_id)
                    .first()
                )
                if taken:
                    raise ConfigError(f"Team name '{name}' already taken")
                team.name = name

            if description is not None:
                team.description = description

            if mode is not None:
                if mode not in ("route", "coordinate", "collaborate"):
                    raise ConfigError(f"Unknown mode '{mode}'")
                team.mode = mode

            if host_agent_id is not None:
                host = session.query(Agent).filter(Agent.agent_id == host_agent_id).first()
                if not host or host.kind != AgentKind.HOST:
                    raise ConfigError(f"Agent {host_agent_id} is not a host agent")
                team.host_agent_id = host_agent_id

            if member_agent_ids is not None:
                if not member_agent_ids:
                    raise ConfigError("A team needs at least one member agent")
                found = {
                    a.agent_id
                    for a in session.query(Agent)
                    .filter(Agent.agent_id.in_(member_agent_ids))
                    .all()
                }
                missing = [i for i in member_agent_ids if i not in found]
                if missing:
                    raise ConfigError(f"Member agent(s) not found: {missing}")

                team.members.clear()
                session.flush()
                for position, agent_id in enumerate(dict.fromkeys(member_agent_ids)):
                    session.add(
                        TeamMember(team_id=team_id, agent_id=agent_id, position=position)
                    )

            if is_active is not None:
                team.is_active = is_active

            session.flush()
            session.refresh(team)
            record = team.to_dict()

        logger.info(f"Updated team id={team_id}")
        return record

    @staticmethod
    def delete_team(team_id: int) -> bool:
        """Delete a team; membership rows cascade."""
        with session_scope() as session:
            team = session.query(Team).filter(Team.team_id == team_id).first()
            if not team:
                return False
            session.delete(team)
        logger.info(f"Deleted team id={team_id}")
        return True

    @staticmethod
    def get_team(team_id: int) -> Optional[Dict[str, Any]]:
        """Fetch one team with its members."""
        with session_scope() as session:
            team = session.query(Team).filter(Team.team_id == team_id).first()
            return team.to_dict() if team else None

    @staticmethod
    def list_teams() -> List[Dict[str, Any]]:
        """List all teams with their members."""
        with session_scope() as session:
            teams = session.query(Team).order_by(Team.team_id).all()
            return [t.to_dict() for t in teams]


# Coordinators are ordinary agents now; kept so old imports do not break.
HostAgentService = AgentService
