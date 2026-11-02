# app/services/auth_service.py
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)

    async def authenticate(self, credentials: LoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_identifier(credentials.username_or_email)
        if not user or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email or password.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive. Please contact administration.",
            )

        # Extract roles and flattened unique permissions
        role_codes = [role.role_code for role in user.roles]
        permission_codes = list(
            {
                perm.permission_code
                for role in user.roles
                for perm in role.permissions
            }
        )

        token = create_access_token(
            subject=str(user.user_id),
            extra_claims={
                "roles": role_codes,
                "display_name": user.display_name,
            },
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=user.user_id,
            username=user.username,
            display_name=user.display_name,
            roles=role_codes,
            permissions=permission_codes,
        )