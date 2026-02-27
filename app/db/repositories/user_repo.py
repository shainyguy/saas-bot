# app/db/repositories/user_repo.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
import secrets

from app.db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str = "ru",
    ) -> tuple[User, bool]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            return user, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            role="user",
            referral_code=secrets.token_urlsafe(8),
            ai_requests_reset_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        self.session.add(user)
        await self.session.flush()
        return user, True

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_admin(self, telegram_id: int) -> bool:
        user = await self.get_by_telegram_id(telegram_id)
        return user is not None and user.role == "admin"

    async def increment_ai_requests(self, telegram_id: int) -> int:
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return 0

        now = datetime.now(timezone.utc)
        if user.ai_requests_reset_at and now >= user.ai_requests_reset_at:
            user.ai_requests_today = 0
            user.ai_requests_reset_at = now + timedelta(days=1)

        user.ai_requests_today += 1
        return user.ai_requests_today
