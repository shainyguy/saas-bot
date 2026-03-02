# app/bot/middlewares/throttling.py
from typing import Callable, Awaitable, Any, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 5, window: int = 10):
        self.rate_limit = rate_limit
        self.window = window

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Throttle только Message, НЕ CallbackQuery
        if isinstance(event, Message) and event.from_user:
            try:
                from app.services.cache.redis_cache import RedisCache
                allowed = await RedisCache.get_rate_limit(
                    user_id=event.from_user.id,
                    action="msg",
                    limit=self.rate_limit,
                    window=self.window,
                )
                if not allowed:
                    await event.answer("⏳ Слишком быстро. Подождите.")
                    return
            except Exception:
                pass

        return await handler(event, data)