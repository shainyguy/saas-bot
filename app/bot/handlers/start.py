# app/bot/handlers/start.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command

from app.bot.keyboards.inline import main_menu_keyboard
from app.config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    is_admin = message.from_user.id in settings.admin_ids_set
    badge = " 👑" if is_admin else ""

    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!{badge}\n\n"
        f"🚀 <b>SaaS Bot</b> — автоматизация контента\n\n"
        f"• 🤖 AI-генерация постов\n"
        f"• 📝 Автопостинг в каналы\n"
        f"• 🔀 Кросспостинг\n"
        f"• ⚡ Триггерная автоматизация\n"
        f"• 📊 Аналитика\n\n"
        f"Выберите действие:",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
            reply_markup=main_menu_keyboard(),
        )
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📚 <b>Команды:</b>\n\n"
        "/start — Главное меню\n"
        "/subscribe — Подписка\n"
        "/tasks — Задачи\n"
        "/help — Справка\n"
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer(
        "🏠 <b>Главное меню</b>",
        reply_markup=main_menu_keyboard(),
    )