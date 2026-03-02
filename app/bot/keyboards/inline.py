# app/bot/keyboards/inline.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.config import settings


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if settings.WEBAPP_URL:
        builder.row(
            InlineKeyboardButton(
                text="📊 Дашборд",
                web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/app"),
            )
        )

    builder.row(
        InlineKeyboardButton(text="🤖 AI Генерация", callback_data="menu_ai"),
        InlineKeyboardButton(text="📝 Автопостинг", callback_data="menu_autopost"),
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Автоматизация", callback_data="menu_automation"),
        InlineKeyboardButton(text="📋 Задачи", callback_data="menu_tasks"),
    )
    builder.row(
        InlineKeyboardButton(text="💎 Подписка", callback_data="menu_subscription"),
        InlineKeyboardButton(text="📈 Статистика", callback_data="menu_stats"),
    )
    return builder.as_markup()


def subscription_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🟢 Starter — 490₽/мес",
            callback_data="pay_starter",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔵 Pro — 1 490₽/мес",
            callback_data="pay_pro",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🟣 Business — 3 990₽/мес",
            callback_data="pay_business",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⚡ Неделя — 390₽",
            callback_data="pay_weekly",
        )
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"),
    )
    return builder.as_markup()


def ai_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✍️ Сгенерировать пост", callback_data="ai_post"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Рерайт текста", callback_data="ai_rewrite"),
    )
    builder.row(
        InlineKeyboardButton(text="💬 Комментарий", callback_data="ai_comment"),
    )
    builder.row(
        InlineKeyboardButton(text="🔀 A/B тест", callback_data="ai_abtest"),
    )
    builder.row(
        InlineKeyboardButton(text="🎯 Построить воронку", callback_data="ai_funnel"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"),
    )
    return builder.as_markup()


def automation_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Создать автопост", callback_data="auto_newpost"),
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Создать триггер", callback_data="auto_newtrigger"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Мои автопосты", callback_data="auto_myposts"),
    )
    builder.row(
        InlineKeyboardButton(text="🤖 Автоответчик", callback_data="auto_responder"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"),
    )
    return builder.as_markup()


def tasks_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Мои задачи", callback_data="tasks_list"),
    )
    builder.row(
        InlineKeyboardButton(text="➕ Новая задача", callback_data="tasks_new"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"),
    )
    return builder.as_markup()


def back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_main"),
    )
    return builder.as_markup()