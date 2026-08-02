"""Authentication and authorization contract tests against the real database."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text

from app.core.config import Settings, get_settings
from app.core.security import ACCESS_TOKEN_COOKIE, hash_password
from app.db.session import async_session_factory, engine
from app.models import User, UserRole
from app.services.auth import seed_admin_user


async def _probe_database() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


@pytest.fixture
def auth_database() -> None:
    try:
        asyncio.run(_probe_database())
    except Exception as exc:  # pragma: no cover - environment-dependent branch
        pytest.skip(f"database unavailable: {type(exc).__name__}")


@pytest.fixture
def user_records(auth_database: None) -> dict[str, str]:
    suffix = uuid4().hex
    emails = {
        "admin": f"auth-admin-{suffix}@example.test",
        "member": f"auth-member-{suffix}@example.test",
        "created": f"auth-created-{suffix}@example.test",
    }

    async def create() -> None:
        async with async_session_factory() as session:
            session.add_all(
                [
                    User(
                        email=emails["admin"],
                        password_hash=hash_password("Admin-password-123"),
                        display_name="测试管理员",
                        role=UserRole.ADMIN,
                    ),
                    User(
                        email=emails["member"],
                        password_hash=hash_password("Member-password-123"),
                        display_name="测试成员",
                        role=UserRole.MEMBER,
                    ),
                ]
            )
            await session.commit()

    asyncio.run(create())
    yield emails

    async def cleanup() -> None:
        async with async_session_factory() as session:
            await session.execute(delete(User).where(User.email.in_(emails.values())))
            await session.commit()

    asyncio.run(cleanup())


def test_missing_and_expired_cookie_return_401(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401

    settings = get_settings()
    expired_token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    client.cookies.set(ACCESS_TOKEN_COOKIE, expired_token)
    assert client.get("/auth/me").status_code == 401


def test_authentication_and_admin_contracts(
    client: TestClient,
    user_records: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    member_login = client.post(
        "/auth/login",
        json={"email": user_records["member"], "password": "Member-password-123"},
    )
    assert member_login.status_code == 200
    assert set(member_login.json()) == {"user"}
    assert "password_hash" not in member_login.text
    assert member_login.json()["user"]["role"] == "member"
    assert "access_token" in member_login.cookies
    assert "HttpOnly" in member_login.headers["set-cookie"]
    assert "SameSite=lax" in member_login.headers["set-cookie"]

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert set(me.json()) == {"id", "email", "display_name", "role"}
    assert "password_hash" not in me.text

    assert client.get("/admin/users").status_code == 403
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401

    wrong_password = client.post(
        "/auth/login",
        json={"email": user_records["member"], "password": "wrong-password"},
    )
    unknown_user = client.post(
        "/auth/login",
        json={"email": "missing@example.test", "password": "wrong-password"},
    )
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.content == unknown_user.content
    assert wrong_password.json() == {"detail": "邮箱或密码错误"}

    admin_login = client.post(
        "/auth/login",
        json={"email": user_records["admin"], "password": "Admin-password-123"},
    )
    assert admin_login.status_code == 200
    created = client.post(
        "/admin/users",
        json={
            "email": user_records["created"],
            "password": "New-member-password-123",
            "display_name": "新成员",
            "role": "member",
        },
    )
    assert created.status_code == 201
    assert set(created.json()) == {"id", "email", "display_name", "role"}
    assert "password_hash" not in created.text

    duplicate = client.post(
        "/admin/users",
        json={
            "email": user_records["created"].upper(),
            "password": "Another-password-123",
            "display_name": "重复成员",
            "role": "member",
        },
    )
    assert duplicate.status_code == 409

    users = client.get("/admin/users")
    assert users.status_code == 200
    assert "password_hash" not in users.text
    assert any(item["email"] == user_records["created"] for item in users.json()["items"])

    assert "*" not in get_settings().cors_origin_list
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    client.cookies.clear()
    production_login = client.post(
        "/auth/login",
        json={"email": user_records["admin"], "password": "Admin-password-123"},
    )
    assert production_login.status_code == 200
    assert "Secure" in production_login.headers["set-cookie"]


def test_seed_admin_is_idempotent(auth_database: None) -> None:
    email = f"seed-admin-{uuid4().hex}@example.test"
    settings = Settings(seed_admin_email=email, seed_admin_password="Seed-password-123")

    async def run_seed_twice() -> tuple[bool, bool, int, str]:
        async with async_session_factory() as session:
            first = await seed_admin_user(session, settings)
            second = await seed_admin_user(session, settings)
            user = await session.scalar(select(User).where(User.email == email))
            count = int(
                await session.scalar(select(func.count(User.id)).where(User.email == email)) or 0
            )
            assert user is not None
            return first, second, count, user.password_hash

    async def cleanup() -> None:
        async with async_session_factory() as session:
            await session.execute(delete(User).where(User.email == email))
            await session.commit()

    try:
        first, second, count, password_hash = asyncio.run(run_seed_twice())
        assert (first, second, count) == (True, False, 1)
        assert password_hash.startswith("$argon2")
    finally:
        asyncio.run(cleanup())
