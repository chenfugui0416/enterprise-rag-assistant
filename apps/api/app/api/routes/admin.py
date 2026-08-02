"""Administrator-only user management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.security import hash_password, normalize_email
from app.db.session import get_db
from app.models import User
from app.schemas.auth import CreateUserRequest, UserListResponse, UserResponse

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    email = normalize_email(request.email)
    existing = await session.scalar(select(User).where(func.lower(User.email) == email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已存在")

    user = User(
        email=email,
        password_hash=hash_password(request.password),
        display_name=request.display_name,
        role=request.role,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已存在") from None
    await session.refresh(user)
    return UserResponse.model_validate(user)


@router.get("", response_model=UserListResponse)
async def list_users(
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserListResponse:
    users = list((await session.scalars(select(User).order_by(User.created_at, User.id))).all())
    return UserListResponse(items=[UserResponse.model_validate(user) for user in users])
