# app/bot/handlers/start.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command

from app.bot.keyboards.inline import main_menu_keyboard, subscription_keyboard
from app.db.models import User
from app.config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User):
    is_admin = message.from_user.id in settings.admin_ids_set
    admin_badge = " 👑 Admin" if is_admin else ""

    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!{admin_badge}\n\n"
        f"🚀 <b>SaaS Bot</b> — автоматизация контента и бизнес-процессов.\n\n"
        f"Что я умею:\n"
        f"• 🤖 AI-генерация постов\n"
        f"• 📝 Автопостинг в каналы\n"
        f"• 🔀 Кросспостинг (VK, Instagram)\n"
        f"• ⚡ Триггерная автоматизация\n"
        f"• 📊 Аналитика вовлечённости\n"
        f"• 🎯 Построение воронок\n\n"
        f"Выберите действие:",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📚 <b>Доступные команды:</b>\n\n"
        "/start — Главное меню\n"
        "/subscribe — Управление подпиской\n"
        "/generate — Сгенерировать пост через AI\n"
        "/autopost — Настроить автопостинг\n"
        "/tasks — Мои задачи\n"
        "/stats — Статистика\n"
        "/settings — Настройки\n"
        "/help — Справка\n"
    )