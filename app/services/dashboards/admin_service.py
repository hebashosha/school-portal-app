from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.dashboards.admin_repo import AdminDashboardRepository
from app.schemas.dashboards.admin import AdminDashboardResponse


class AdminDashboardService:
    def __init__(self, db: AsyncSession):
        self.repo = AdminDashboardRepository(db)

    async def get_dashboard(self) -> AdminDashboardResponse:
        user_counts = await self.repo.get_user_counts_by_role()
        totals = await self.repo.get_user_status_totals()
        structure = await self.repo.get_academic_structure_counts()
        year = await self.repo.get_active_academic_year()
        attendance = await self.repo.get_today_attendance_summary()
        audits = await self.repo.get_recent_audit_count()

        return AdminDashboardResponse(
            user_counts_by_role=user_counts,
            total_users=totals["total"],
            active_users=totals["active"],
            inactive_users=totals["inactive"],
            active_academic_year=year,
            total_grades=structure["grades"],
            total_classes=structure["classes"],
            total_subjects=structure["subjects"],
            today_attendance_summary=attendance,
            recent_audit_count=audits,
        )