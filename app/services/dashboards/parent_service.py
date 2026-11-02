from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.dashboards.parent_repo import ParentDashboardRepository
from app.schemas.dashboards.parent import LinkedStudentCard, ParentDashboardResponse


class ParentDashboardService:
    def __init__(self, db: AsyncSession):
        self.repo = ParentDashboardRepository(db)

    async def get_dashboard(self, parent_user: User) -> ParentDashboardResponse:
        children = await self.repo.get_linked_students(parent_user.user_id)
        cards: List[LinkedStudentCard] = []

        for st in children:
            att = await self.repo.get_child_today_attendance(st.student_id)
            hw = await self.repo.get_child_pending_homework_count(st.student_id)
            cards.append(
                LinkedStudentCard(
                    student_id=st.student_id,
                    student_code=st.student_code,
                    full_name=f"{st.first_name} {st.last_name}",
                    today_attendance=att or "NOT_RECORDED",
                    pending_homework_count=hw,
                )
            )

        return ParentDashboardResponse(
            parent_name=parent_user.display_name,
            total_linked_children=len(cards),
            children=cards,
        )