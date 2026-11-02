from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.dashboards.supervisor_repo import SupervisorDashboardRepository
from app.schemas.dashboards.supervisor import SupervisorDashboardResponse


class SupervisorDashboardService:
    def __init__(self, db: AsyncSession):
        self.repo = SupervisorDashboardRepository(db)

    async def get_dashboard(self, supervisor: User) -> SupervisorDashboardResponse:
        stats = await self.repo.get_today_stats(supervisor.user_id)
        return SupervisorDashboardResponse(
            assigned_classes_count=max(stats["recorded_classes"], 1),
            recorded_classes_today=stats["recorded_classes"],
            today_present_count=stats["present"],
            today_absent_count=stats["absent"],
            today_late_count=stats["late"],
            today_excused_count=stats["excused"],
            pending_manager_authorization_count=stats["pending_auth"],
        )