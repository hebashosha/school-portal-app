from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.dashboards.assistant_teacher_repo import AssistantTeacherDashboardRepository
from app.schemas.dashboards.assistant_teacher import AssistantTeacherDashboardResponse


class AssistantTeacherDashboardService:
    def __init__(self, db: AsyncSession):
        self.repo = AssistantTeacherDashboardRepository(db)

    async def get_dashboard(self, assistant_user: User) -> AssistantTeacherDashboardResponse:
        staff = await self.repo.get_staff_by_user_id(assistant_user.user_id)
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant Teacher profile not found for this user account.",
            )

        unsubmitted = await self.repo.get_unsubmitted_students_count()
        return AssistantTeacherDashboardResponse(
            staff_code=staff.employee_code,
            active_assignments_to_follow=0,
            unsubmitted_students_count=unsubmitted,
        )