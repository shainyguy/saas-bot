# app/bot/handlers/admin.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from app.bot.filters.admin import AdminFilter
from app.bot.keyboards.inline import back_keyboard
from app.services.cache.redis_cache import RedisCache

router = Router()
router.message.filter(AdminFilter())


@router.message(Command("admin"))
async def admin_panel(message: Message):
    analytics = await RedisCache.get("analytics:dashboard") or {}

    await message.answer(
        f"👑 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: <b>{analytics.get('total_users', '—')}</b>\n"
        f"🕐 Обновлено: {analytics.get('updated_at', '—')}\n\n"
        f"/broadcast текст — рассылка\n"
    )


@router.message(Command("broadcast"))
async def admin_broadcast(message: Message):
    text = (message.text or "").replace("/broadcast", "").strip()
    if not text:
        await message.answer("Используйте: /broadcast текст сообщения")
        return

    try:
        from app.db.database import Database
        from sqlalchemy import select
        from app.db.models import User

        async with Database.session() as session:
            result = await session.execute(
                select(User.telegram_id).where(User.is_blocked == False)
            )
            user_ids = [row[0] for row in result.all()]

        sent = 0
        failed = 0
        for uid in user_ids:
            try:
                await message.bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1

        await message.answer(f"📤 Отправлено: {sent}, ошибок: {failed}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")