# app/bot/middlewares/subscription.py
from typing import Callable, Awaitable, Any, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.config import settings
from app.db.database import Database
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.services.cache.redis_cache import RedisCache


class SubscriptionMiddleware(BaseMiddleware):
    """Middleware для проверки подписки перед premium-командами."""

    PREMIUM_COMMANDS = {
        "/autopost", "/crosspost", "/ai", "/generate",
        "/trigger", "/funnel", "/abtest",
    }

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            # Админы — без ограничений
            if event.from_user.id in settings.admin_ids_set:
                data["plan_limits"] = {k: -1 for k in ["channels", "tasks", "ai_requests_daily"]}
                data["plan_limits"].update({
                    "crosspost": True, "google_sheets": True,
                    "crm_integration": True, "ab_testing": True,
                    "triggers": -1, "autopost_daily": -1,
                })
                return await handler(event, data)

            # Проверить команду
            text = event.text or ""
            cmd = text.split()[0] if text else ""

            if cmd in self.PREMIUM_COMMANDS:
                user_id = event.from_user.id

                # Кэш
                cached = await RedisCache.get(f"sub:{user_id}")
                if cached:
                    data["plan_limits"] = cached
                    return await handler(event, data)

                async with Database.session() as session:
                    sub_repo = SubscriptionRepository(session)
                    limits = await sub_repo.get_plan_limits(user_id)
                    await RedisCache.set(f"sub:{user_id}", limits, ttl=300)
                    data["plan_limits"] = limits

        return await handler(event, data)