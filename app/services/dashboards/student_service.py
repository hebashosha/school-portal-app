from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.dashboards.student_repo import StudentDashboardRepository
from app.schemas.dashboards.student import StudentDashboardResponse, StudentTaskItem


class StudentDashboardService:
    def __init__(self, db: AsyncSession):
        self.repo = StudentDashboardRepository(db)

    async def get_dashboard(self, student_user: User) -> StudentDashboardResponse:
        student = await self.repo.get_student_by_user_id(student_user.user_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found for this user account.",
            )

        today_status = await self.repo.get_today_attendance(student.student_id)
        submissions = await self.repo.get_recent_submissions(student.student_id)

        tasks: List[StudentTaskItem] = [
            StudentTaskItem(
                id=s.submission_id,
                title=f"Submission Attempt #{s.attempt_number}",
                item_type="ASSIGNMENT",
                due_at=s.submitted_at,
                status=s.status,
                awarded_score=s.awarded_score,
            )
            for s in submissions
        ]

        return StudentDashboardResponse(
            student_code=student.student_code,
            student_name=f"{student.first_name} {student.last_name}",
            today_attendance_status=today_status or "NOT_RECORDED",
            upcoming_tasks=tasks,
        )