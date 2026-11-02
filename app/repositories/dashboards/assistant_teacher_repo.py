import uuid
from typing import Optional
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coursework import AssignmentSubmission
from app.models.stakeholder import StaffMember, Student


class AssistantTeacherDashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_staff_by_user_id(self, user_id: uuid.UUID) -> Optional[StaffMember]:
        stmt = select(StaffMember).where(StaffMember.user_id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_unsubmitted_students_count(self) -> int:
        stmt = (
            select(func.count(distinct(Student.student_id)))
            .join(AssignmentSubmission, Student.student_id == AssignmentSubmission.student_id, isouter=True)
            .where(AssignmentSubmission.submission_id.is_(None), Student.status == "ACTIVE")
        )
        return (await self.db.execute(stmt)).scalar() or 0