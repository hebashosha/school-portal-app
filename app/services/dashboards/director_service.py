from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.dashboards.director_repo import DirectorDashboardRepository
from app.schemas.dashboards.director import DirectorDashboardResponse


class DirectorDashboardService:
    def __init__(self, db: AsyncSession):
        self.repo = DirectorDashboardRepository(db)

    async def get_dashboard(self) -> DirectorDashboardResponse:
        unauth = await self.repo.get_unauthorized_late_excused_count()
        pending_changes = await self.repo.get_pending_attendance_change_requests_count()
        attendance = await self.repo.get_today_attendance_summary()
        total_pending = unauth["LATE"] + unauth["EXCUSED"] + pending_changes

        return DirectorDashboardResponse(
            pending_approvals_count=total_pending,
            pending_late_approvals=unauth["LATE"],
            pending_excused_approvals=unauth["EXCUSED"],
            pending_attendance_changes=pending_changes,
            today_attendance_summary=attendance,
            recent_approvals_queue=[],
        )