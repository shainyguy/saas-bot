# app/bot/middlewares/auth.py
from typing import Callable, Awaitable, Any, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.db.database import Database
from app.db.repositories.user_repo import UserRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if not user:
            return await handler(event, data)

        async with Database.session() as session:
            repo = UserRepository(session)
            db_user, created = await repo.get_or_create(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code or "ru",
            )

            if created:
                sub_repo = SubscriptionRepository(session)
                await sub_repo.create_trial(user.id)

            if db_user.is_blocked:
                if isinstance(event, Message):
                    await event.answer("🚫 Ваш аккаунт заблокирован.")
                return

            data["db_user"] = db_user

        return await handler(event, data)