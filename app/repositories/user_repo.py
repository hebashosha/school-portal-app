# app/repositories/user_repo.py
import uuid
from typing import Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import Role, User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_identifier(self, identifier: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
            )
            .where(
                or_(
                    User.username == identifier,
                    User.email == identifier,
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
            )
            .where(User.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    async def get_all(self, skip: int = 0, limit: int = 50) -> List[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_role_by_code(self, role_code: str) -> Optional[Role]:
        stmt = select(Role).where(Role.role_code == role_code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        return user