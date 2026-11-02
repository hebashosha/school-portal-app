from datetime import date
from typing import Dict, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import AcademicYear, ClassModel, Grade, Subject
from app.models.attendance import AttendanceOccurrence, AttendanceRecord
from app.models.system import AuditLog
from app.models.user import Role, User, UserRole


class AdminDashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_counts_by_role(self) -> Dict[str, int]:
        stmt = (
            select(Role.role_code, func.count(UserRole.user_id))
            .join(UserRole, Role.role_id == UserRole.role_id, isouter=True)
            .group_by(Role.role_code)
        )
        res = await self.db.execute(stmt)
        return {code: cnt for code, cnt in res.fetchall()}

    async def get_user_status_totals(self) -> Dict[str, int]:
        total = (await self.db.execute(select(func.count(User.user_id)))).scalar() or 0
        active = (await self.db.execute(select(func.count(User.user_id)).where(User.is_active.is_(True)))).scalar() or 0
        return {"total": total, "active": active, "inactive": max(0, total - active)}

    async def get_academic_structure_counts(self) -> Dict[str, int]:
        grades = (await self.db.execute(select(func.count(Grade.grade_id)))).scalar() or 0
        classes = (await self.db.execute(select(func.count(ClassModel.class_id)))).scalar() or 0
        subjects = (await self.db.execute(select(func.count(Subject.subject_id)))).scalar() or 0
        return {"grades": grades, "classes": classes, "subjects": subjects}

    async def get_active_academic_year(self) -> Optional[str]:
        stmt = select(AcademicYear.name).where(AcademicYear.is_active.is_(True))
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_today_attendance_summary(self) -> Dict[str, int]:
        today = date.today()
        stmt = (
            select(AttendanceRecord.status, func.count(AttendanceRecord.attendance_record_id))
            .join(AttendanceOccurrence, AttendanceRecord.occurrence_id == AttendanceOccurrence.occurrence_id)
            .where(AttendanceOccurrence.occurrence_date == today)
            .group_by(AttendanceRecord.status)
        )
        res = await self.db.execute(stmt)
        summary = {"PRESENT": 0, "ABSENT": 0, "LATE": 0, "EXCUSED": 0}
        for st, cnt in res.fetchall():
            if st.upper() in summary:
                summary[st.upper()] = cnt
        return summary

    async def get_recent_audit_count(self) -> int:
        stmt = select(func.count(AuditLog.audit_id))
        return (await self.db.execute(stmt)).scalar() or 0