# app/services/user_service.py
import uuid
from typing import List, Optional
from fastapi import HTTPException, status

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate

# Allowed core roles from the specification (04.5.8)
VALID_ROLES = {
    "SCHOOL_ADMIN",
    "DIRECTOR",
    "FLOOR_SUPERVISOR",
    "TEACHER",
    "ASSISTANT_TEACHER",
    "STUDENT",
    "PARENT",
}


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def get_by_identifier(self, identifier: str) -> Optional[User]:
        return await self.user_repo.get_by_identifier(identifier)

    async def register_user(self, payload: UserCreate) -> User:
        # 1. Check uniqueness of username and email
        existing_username = await self.user_repo.get_by_identifier(payload.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{payload.username}' is already in use.",
            )

        existing_email = await self.user_repo.get_by_identifier(payload.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{payload.email}' is already registered.",
            )

        # 2. Validate all provided role codes before creating the user
        roles_to_assign = []
        for role_code in set(payload.roles):
            role_code_clean = role_code.strip().upper()
            if role_code_clean not in VALID_ROLES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role '{role_code}'. Allowed roles: {sorted(list(VALID_ROLES))}",
                )

            role_entity = await self.user_repo.get_role_by_code(role_code_clean)
            if not role_entity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role '{role_code_clean}' does not exist in the database. Please run the seeder.",
                )
            roles_to_assign.append(role_entity)

        # 3. Create the user entity
        new_user = User(
            username=payload.username,
            email=payload.email,
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
            phone=payload.phone,
            is_active=True,
        )

        # 4. Attach the dynamic roles selected by the client
        for role in roles_to_assign:
            new_user.roles.append(role)

        created_user = await self.user_repo.create(new_user)
        return created_user