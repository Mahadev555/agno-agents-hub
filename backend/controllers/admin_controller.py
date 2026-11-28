"""Administrator-only dashboard operations."""

from typing import Any, Dict, Optional

from fastapi import HTTPException

from services.admin_service import AdminService


class AdminController:
    """Expose safe, paginated account and execution data to admins."""

    @staticmethod
    def overview() -> Dict[str, Any]:
        return AdminService.get_overview()

    @staticmethod
    def users(
        limit: int = 50, offset: int = 0, search: Optional[str] = None
    ) -> Dict[str, Any]:
        return AdminService.list_users(limit=limit, offset=offset, search=search)

    @staticmethod
    def agents(
        limit: int = 50, offset: int = 0, search: Optional[str] = None
    ) -> Dict[str, Any]:
        return AdminService.list_agents(limit=limit, offset=offset, search=search)

    @staticmethod
    def teams(
        limit: int = 50, offset: int = 0, search: Optional[str] = None
    ) -> Dict[str, Any]:
        return AdminService.list_teams(limit=limit, offset=offset, search=search)

    @staticmethod
    def runs(
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        return AdminService.list_runs(
            limit=limit, offset=offset, status=status, user_id=user_id
        )

    @staticmethod
    def run(run_id: str) -> Dict[str, Any]:
        record = AdminService.get_run(run_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return record
