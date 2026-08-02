"""Authentication persistence helpers, including the optional seed administrator."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import hash_password, normalize_email
from app.db.session import async_session_factory
from app.models import User, UserRole

logger = logging.getLogger(__name__)


async def seed_admin_user(session: AsyncSession, settings: Settings | None = None) -> bool:
    """Create the configured administrator once, without changing an existing account."""
    settings = settings or get_settings()
    email = normalize_email(settings.seed_admin_email)
    password = settings.seed_admin_password
    if not email or not password:
        logger.warning("SEED_ADMIN_EMAIL/SEED_ADMIN_PASSWORD 未配置，跳过种子管理员创建")
        return False

    existing = await session.scalar(select(User).where(func.lower(User.email) == email))
    if existing is not None:
        logger.info("种子管理员已存在，跳过创建: %s", email)
        return False

    session.add(
        User(
            email=email,
            password_hash=hash_password(password),
            display_name="管理员",
            role=UserRole.ADMIN,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.info("种子管理员已由其他进程创建，跳过重复创建: %s", email)
        return False
    logger.info("已创建种子管理员: %s", email)
    return True


async def seed_admin_on_startup() -> None:
    """Run seed creation during application startup when both variables are set."""
    settings = get_settings()
    if not settings.seed_admin_email or not settings.seed_admin_password:
        logger.warning("SEED_ADMIN_EMAIL/SEED_ADMIN_PASSWORD 未配置，跳过种子管理员创建")
        return
    async with async_session_factory() as session:
        await seed_admin_user(session, settings)
