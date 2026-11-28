"""Read-only, paginated views for administrator operations."""

from typing import Any, Dict, Optional

from sqlalchemy import func, or_

from connection import session_scope
from models.agent import Agent, Team
from models.run import Run
from models.user import User


class AdminService:
    """Aggregate and list account, resource, and execution data for admins."""

    @staticmethod
    def get_overview() -> Dict[str, Any]:
        with session_scope() as session:
            status_counts = dict(
                session.query(Run.status, func.count(Run.run_id))
                .group_by(Run.status)
                .all()
            )
            total_tokens = session.query(func.coalesce(func.sum(Run.total_tokens), 0)).scalar()
            return {
                "users": {
                    "total": session.query(func.count(User.user_id)).scalar() or 0,
                    "active": session.query(func.count(User.user_id))
                    .filter(User.is_active.is_(True))
                    .scalar()
                    or 0,
                    "admins": session.query(func.count(User.user_id))
                    .filter(User.is_admin.is_(True))
                    .scalar()
                    or 0,
                },
                "agents": {
                    "total": session.query(func.count(Agent.agent_id)).scalar() or 0,
                    "active": session.query(func.count(Agent.agent_id))
                    .filter(Agent.is_active.is_(True))
                    .scalar()
                    or 0,
                },
                "teams": {
                    "total": session.query(func.count(Team.team_id)).scalar() or 0,
                    "active": session.query(func.count(Team.team_id))
                    .filter(Team.is_active.is_(True))
                    .scalar()
                    or 0,
                },
                "runs": {
                    "total": session.query(func.count(Run.run_id)).scalar() or 0,
                    "by_status": status_counts,
                    "total_tokens": int(total_tokens or 0),
                },
            }

    @staticmethod
    def list_users(
        limit: int = 50, offset: int = 0, search: Optional[str] = None
    ) -> Dict[str, Any]:
        with session_scope() as session:
            run_counts = (
                session.query(
                    Run.owner_id.label("owner_id"),
                    func.count(Run.run_id).label("run_count"),
                )
                .group_by(Run.owner_id)
                .subquery()
            )
            query = (
                session.query(User, func.coalesce(run_counts.c.run_count, 0))
                .outerjoin(run_counts, run_counts.c.owner_id == User.user_id)
            )
            if search and search.strip():
                term = f"%{search.strip()}%"
                query = query.filter(
                    or_(User.email.ilike(term), User.display_name.ilike(term))
                )

            total = query.count()
            records = (
                query.order_by(User.created_at.desc(), User.user_id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            items = []
            for user, run_count in records:
                item = user.to_dict()
                item["run_count"] = int(run_count)
                items.append(item)

            return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    def list_agents(
        limit: int = 50, offset: int = 0, search: Optional[str] = None
    ) -> Dict[str, Any]:
        with session_scope() as session:
            query = session.query(Agent, User).outerjoin(User, Agent.owner_id == User.user_id)
            if search and search.strip():
                term = f"%{search.strip()}%"
                query = query.filter(
                    or_(Agent.name.ilike(term), Agent.description.ilike(term))
                )

            total = query.count()
            records = (
                query.order_by(Agent.created_at.desc(), Agent.agent_id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            items = [
                {
                    "agent_id": agent.agent_id,
                    "name": agent.name,
                    "description": agent.description,
                    "kind": agent.kind,
                    "is_active": agent.is_active,
                    "is_public": agent.is_public,
                    "owner_id": agent.owner_id,
                    "owner_email": owner.email if owner else None,
                    "owner_display_name": owner.display_name if owner else None,
                    "created_at": agent.created_at.isoformat() if agent.created_at else None,
                    "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
                }
                for agent, owner in records
            ]
            return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    def list_teams(
        limit: int = 50, offset: int = 0, search: Optional[str] = None
    ) -> Dict[str, Any]:
        with session_scope() as session:
            query = session.query(Team, User).outerjoin(User, Team.owner_id == User.user_id)
            if search and search.strip():
                term = f"%{search.strip()}%"
                query = query.filter(
                    or_(Team.name.ilike(term), Team.description.ilike(term))
                )

            total = query.count()
            records = (
                query.order_by(Team.created_at.desc(), Team.team_id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            items = []
            for team, owner in records:
                items.append(
                    {
                        "team_id": team.team_id,
                        "name": team.name,
                        "description": team.description,
                        "host_agent_id": team.host_agent_id,
                        "host_agent_name": team.host_agent.name if team.host_agent else None,
                        "mode": team.mode,
                        "is_active": team.is_active,
                        "is_public": team.is_public,
                        "owner_id": team.owner_id,
                        "owner_email": owner.email if owner else None,
                        "owner_display_name": owner.display_name if owner else None,
                        "member_count": len(team.members),
                        "member_names": [
                            member.agent.name for member in team.members if member.agent
                        ],
                        "created_at": team.created_at.isoformat() if team.created_at else None,
                        "updated_at": team.updated_at.isoformat() if team.updated_at else None,
                    }
                )
            return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    def list_runs(
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        with session_scope() as session:
            query = session.query(Run, User).outerjoin(User, Run.owner_id == User.user_id)
            if status:
                query = query.filter(Run.status == status)
            if user_id is not None:
                query = query.filter(Run.owner_id == user_id)

            total = query.count()
            records = (
                query.order_by(Run.created_at.desc(), Run.run_id.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            items = []
            for run, owner in records:
                item = {
                    "run_id": run.run_id,
                    "status": run.status,
                    "mode": run.mode,
                    "prompt_preview": (run.prompt or "")[:300],
                    "agent_ids": run.agent_ids or [],
                    "host_agent_id": run.host_agent_id,
                    "owner_id": run.owner_id,
                    "owner_email": owner.email if owner else None,
                    "owner_display_name": owner.display_name if owner else None,
                    "input_tokens": run.input_tokens,
                    "output_tokens": run.output_tokens,
                    "total_tokens": run.total_tokens,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                    "duration_ms": run.duration_ms,
                }
                items.append(item)
            return {"items": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    def get_run(run_id: str) -> Optional[Dict[str, Any]]:
        with session_scope() as session:
            record = (
                session.query(Run, User)
                .outerjoin(User, Run.owner_id == User.user_id)
                .filter(Run.run_id == run_id)
                .first()
            )
            if not record:
                return None

            run, owner = record
            item = run.to_dict()
            item["owner_email"] = owner.email if owner else None
            item["owner_display_name"] = owner.display_name if owner else None
            return item
