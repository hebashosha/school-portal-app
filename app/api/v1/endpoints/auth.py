# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserProfileResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    return await service.authenticate(credentials)


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    role_codes = [role.role_code for role in current_user.roles]
    permission_codes = list(
        {
            perm.permission_code
            for role in current_user.roles
            for perm in role.permissions
        }
    )

    return UserProfileResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        display_name=current_user.display_name,
        phone=current_user.phone,
        is_active=current_user.is_active,
        roles=role_codes,
        permissions=permission_codes,
    )