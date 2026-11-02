from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.dashboards.teacher_repo import TeacherDashboardRepository
from app.schemas.dashboards.teacher import HomeworkCard, TeacherDashboardResponse


class TeacherDashboardService:
    def __init__(self, db: AsyncSession):
        self.repo = TeacherDashboardRepository(db)

    async def get_dashboard(self, teacher_user: User) -> TeacherDashboardResponse:
        staff = await self.repo.get_staff_by_user_id(teacher_user.user_id)
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Teacher profile not found for this user account.",
            )

        assignments = await self.repo.get_teacher_assignments(staff.staff_id)
        pending_grading = await self.repo.get_pending_grading_count(staff.staff_id)

        cards: List[HomeworkCard] = []
        for a in assignments:
            m = await self.repo.get_assignment_metrics(a.assignment_id)
            cards.append(
                HomeworkCard(
                    assignment_id=a.assignment_id,
                    title=a.title,
                    class_id=a.class_id,
                    due_at=a.due_at,
                    submitted_count=m["submitted"],
                    graded_count=m["graded"],
                )
            )

        return TeacherDashboardResponse(
            staff_code=staff.employee_code,
            active_assignments_count=len(assignments),
            pending_grading_count=pending_grading,
            recent_assignments=cards,
        )