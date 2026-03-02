# app/bot/middlewares/subscription.py
from typing import Callable, Awaitable, Any, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.config import settings


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Всегда пропускаем — проверка внутри хендлеров при необходимости
        # Не блокируем никакие callback'и и сообщения
        return await handler(event, data)