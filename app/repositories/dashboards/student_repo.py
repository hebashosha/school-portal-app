import uuid
from datetime import date
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import AttendanceOccurrence, AttendanceRecord
from app.models.coursework import AssignmentSubmission
from app.models.stakeholder import Student


class StudentDashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_student_by_user_id(self, user_id: uuid.UUID) -> Optional[Student]:
        stmt = select(Student).where(Student.user_id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_today_attendance(self, student_id: uuid.UUID) -> Optional[str]:
        today = date.today()
        stmt = (
            select(AttendanceRecord.status)
            .join(AttendanceOccurrence, AttendanceRecord.occurrence_id == AttendanceOccurrence.occurrence_id)
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceOccurrence.occurrence_date == today,
            )
            .order_by(AttendanceOccurrence.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_recent_submissions(self, student_id: uuid.UUID) -> List[AssignmentSubmission]:
        stmt = (
            select(AssignmentSubmission)
            .where(AssignmentSubmission.student_id == student_id)
            .order_by(AssignmentSubmission.submitted_at.desc())
            .limit(5)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())