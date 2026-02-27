# app/bot/keyboards/inline.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings, PlanType


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Дашборд", web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/app")),
    )
    builder.row(
        InlineKeyboardButton(text="🤖 AI Генерация", callback_data="ai_menu"),
        InlineKeyboardButton(text="📝 Автопостинг", callback_data="autopost_menu"),
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Автоматизация", callback_data="automation_menu"),
        InlineKeyboardButton(text="📈 Аналитика", callback_data="analytics_menu"),
    )
    builder.row(
        InlineKeyboardButton(text="💎 Подписка", callback_data="subscription_menu"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings_menu"),
    )
    return builder.as_markup()


def subscription_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🟢 Starter — 490₽/мес",
            callback_data=f"subscribe:{PlanType.STARTER.value}",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔵 Pro — 1 490₽/мес",
            callback_data=f"subscribe:{PlanType.PRO.value}",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🟣 Business — 3 990₽/мес",
            callback_data=f"subscribe:{PlanType.BUSINESS.value}",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="⚡ Неделя — 390₽",
            callback_data=f"subscribe:{PlanType.WEEKLY.value}",
        ),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"),
    )
    return builder.as_markup()


def ai_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✍️ Сгенерировать пост", callback_data="ai:generate_post"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Рерайт текста", callback_data="ai:rewrite"),
    )
    builder.row(
        InlineKeyboardButton(text="💬 Сгенерировать комментарий", callback_data="ai:comment"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Анализ вовлечённости", callback_data="ai:engagement"),
    )
    builder.row(
        InlineKeyboardButton(text="🔀 A/B тест текста", callback_data="ai:abtest"),
    )
    builder.row(
        InlineKeyboardButton(text="🎯 Построить воронку", callback_data="ai:funnel"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"),
    )
    return builder.as_markup()


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm:{action}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
    )
    return builder.as_markup()