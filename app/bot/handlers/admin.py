# app/bot/handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from app.bot.filters.admin import AdminFilter
from app.db.database import Database
from app.db.repositories.user_repo import UserRepository
from app.services.cache.redis_cache import RedisCache
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()
router.message.filter(AdminFilter())


@router.message(Command("admin"))
async def admin_panel(message: Message):
    analytics = await RedisCache.get("analytics:dashboard") or {}

    await message.answer(
        f"👑 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: <b>{analytics.get('total_users', '—')}</b>\n"
        f"💎 Активных подписок: <b>{analytics.get('active_subscriptions', '—')}</b>\n"
        f"📝 Постов сегодня: <b>{analytics.get('posts_today', '—')}</b>\n"
        f"🕐 Обновлено: {analytics.get('updated_at', '—')}\n\n"
        f"/broadcast — рассылка\n"
        f"/users_stats — детальная статистика\n"
        f"/block <user_id> — заблокировать\n"
    )


@router.message(Command("broadcast"))
async def admin_broadcast(message: Message):
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("Используйте: /broadcast <текст сообщения>")
        return

    async with Database.session() as session:
        from sqlalchemy import select
        from app.db.models import User
        result = await session.execute(select(User.telegram_id).where(User.is_blocked == False))
        user_ids = [row[0] for row in result.all()]

    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await message.bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"📤 Рассылка завершена\n"
        f"✅ Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )