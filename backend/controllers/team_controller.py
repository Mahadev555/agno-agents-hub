"""
Team Controller

CRUD for saved teams, plus resolving a team into the configs needed to run it.

Persisting composition means a team can be named, reused, and shared instead of
being re-specified by the client on every request.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

from dependencies import can_read, require_owner
from services.agent_service import ConfigError, TeamService
from services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class TeamCreateRequest(BaseModel):
    """Request model for creating a team."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    hostAgentId: int = Field(..., description="Coordinator agent id (kind='host')")
    memberAgentIds: List[int] = Field(..., min_length=1)
    mode: str = Field(default="coordinate")
    config: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = False


class TeamUpdateRequest(BaseModel):
    """Request model for updating a team. Members are replaced wholesale."""

    name: Optional[str] = None
    description: Optional[str] = None
    hostAgentId: Optional[int] = None
    memberAgentIds: Optional[List[int]] = None
    mode: Optional[str] = None
    is_active: Optional[bool] = None


class TeamsController:
    """Handles team management operations."""

    @staticmethod
    async def list_teams(user: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List teams the caller may see."""
        return [t for t in TeamService.list_teams() if can_read(t, user)]

    @staticmethod
    async def get_team(team_id: int, user: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one team the caller may see."""
        team = TeamService.get_team(team_id)
        if not team or not can_read(team, user):
            raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
        return team

    @staticmethod
    async def create_team(payload: TeamCreateRequest, user: Dict[str, Any]) -> Dict[str, Any]:
        """Create a team owned by the caller."""
        try:
            return TeamService.create_team(
                name=payload.name,
                description=payload.description,
                host_agent_id=payload.hostAgentId,
                member_agent_ids=payload.memberAgentIds,
                mode=payload.mode,
                config=payload.config,
                owner_id=user["user_id"],
                is_public=bool(payload.is_public),
            )
        except ConfigError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    async def update_team(
        team_id: int, payload: TeamUpdateRequest, user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a team the caller owns."""
        existing = TeamService.get_team(team_id)
        if not existing or not can_read(existing, user):
            raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
        require_owner(existing, user, "team")

        try:
            return TeamService.update_team(
                team_id=team_id,
                name=payload.name,
                description=payload.description,
                host_agent_id=payload.hostAgentId,
                member_agent_ids=payload.memberAgentIds,
                mode=payload.mode,
                is_active=payload.is_active,
            )
        except ConfigError as e:
            # Distinguish "no such team" from a bad request.
            status = 404 if "not found" in str(e).lower() and "member" not in str(e).lower() else 400
            raise HTTPException(status_code=status, detail=str(e))

    @staticmethod
    async def delete_team(team_id: int, user: Dict[str, Any]) -> Dict[str, str]:
        """Delete a team the caller owns."""
        existing = TeamService.get_team(team_id)
        if not existing or not can_read(existing, user):
            raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
        require_owner(existing, user, "team")

        if not TeamService.delete_team(team_id):
            raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
        return {"message": f"Team {team_id} deleted successfully"}

    @staticmethod
    def resolve_for_run(team_id: int, user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load everything needed to execute a team.

        Returns the host config (with the team's mode applied) and the member
        agent rows in their stored order. Running a team only needs read access,
        so a public team can be used by anyone signed in.
        """
        team = TeamService.get_team(team_id)
        if not team or not can_read(team, user):
            raise HTTPException(status_code=404, detail=f"Team {team_id} not found")
        if not team.get("is_active", True):
            raise HTTPException(status_code=400, detail=f"Team {team_id} is inactive")

        host = DatabaseService.get_host_agent_by_id(team["host_agent_id"])
        if not host:
            raise HTTPException(
                status_code=409,
                detail=f"Team {team_id} references missing host agent {team['host_agent_id']}",
            )

        member_ids = [m["agent_id"] for m in team.get("members", [])]
        members = DatabaseService.get_agents_by_ids(member_ids)
        found = {m["agent_id"] for m in members}
        missing = [i for i in member_ids if i not in found]
        if missing:
            raise HTTPException(
                status_code=409,
                detail=f"Team {team_id} references missing member agent(s): {missing}",
            )

        host_config = dict(host.get("config") or {})
        # The team's mode wins: the same coordinator can drive different teams
        # in different modes.
        host_config["mode"] = team["mode"]
        host_config.setdefault("name", team["name"])

        return {
            "team": team,
            "host_agent_id": team["host_agent_id"],
            "host_config": host_config,
            "agents": members,
        }
