# app/services/user_service.py
from fastapi import HTTPException, status
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def create_user(self, payload: UserCreate) -> User:
        if await self.user_repo.get_by_email(payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists."
            )
        if await self.user_repo.get_by_username(payload.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this username already exists."
            )

        user = User(
            username=payload.username,
            email=payload.email,
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
            phone=payload.phone,
        )
        return await self.user_repo.create(user)