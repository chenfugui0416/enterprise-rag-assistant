"""Pydantic contracts for authentication and user administration."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str | None
    role: UserRole


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    user: UserResponse


class CreateUserRequest(LoginRequest):
    display_name: str | None = Field(default=None, max_length=120)
    role: UserRole = UserRole.MEMBER


class UserListResponse(BaseModel):
    items: list[UserResponse]
