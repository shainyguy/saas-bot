# app/bot/handlers/subscription.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from app.bot.keyboards.inline import subscription_keyboard
from app.config import PlanType, settings
from app.db.database import Database
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.services.payments.yukassa import PaymentService
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


@router.message(Command("subscribe"))
@router.callback_query(F.data == "subscription_menu")
async def show_subscription(event: Message | CallbackQuery):
    user_id = event.from_user.id

    # Получить текущую подписку
    async with Database.session() as session:
        sub_repo = SubscriptionRepository(session)
        current_sub = await sub_repo.get_active(user_id)

    if current_sub:
        plan_name = current_sub.plan.upper()
        status = current_sub.status.value
        expires = current_sub.expires_at.strftime("%d.%m.%Y %H:%M") if current_sub.expires_at else "∞"

        text = (
            f"💎 <b>Ваша подписка</b>\n\n"
            f"📋 План: <b>{plan_name}</b>\n"
            f"📊 Статус: <b>{status}</b>\n"
            f"📅 До: <b>{expires}</b>\n\n"
            f"Выберите план для продления/смены:"
        )
    else:
        text = (
            "💎 <b>Тарифные планы</b>\n\n"
            "🟢 <b>Starter</b> — 490₽/мес\n"
            "  • 3 канала, 50 задач, 100 AI-запросов/день\n\n"
            "🔵 <b>Pro</b> — 1 490₽/мес\n"
            "  • 10 каналов, кросспостинг, CRM, A/B тесты\n\n"
            "🟣 <b>Business</b> — 3 990₽/мес\n"
            "  • Без лимитов\n\n"
            "⚡ <b>Неделя</b> — 390₽\n"
            "  • Полный доступ на 7 дней\n"
        )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=subscription_keyboard())
        await event.answer()
    else:
        await event.answer(text, reply_markup=subscription_keyboard())


@router.callback_query(F.data.startswith("subscribe:"))
async def process_subscribe(callback: CallbackQuery):
    plan_str = callback.data.split(":")[1]
    user_id = callback.from_user.id

    # Админ — бесплатно
    if user_id in settings.admin_ids_set:
        async with Database.session() as session:
            sub_repo = SubscriptionRepository(session)
            await sub_repo.activate(user_id, PlanType(plan_str), duration_days=365)

        await callback.message.edit_text(
            f"👑 Подписка <b>{plan_str.upper()}</b> активирована (Admin)."
        )
        await callback.answer("✅ Активировано!")
        return

    try:
        plan = PlanType(plan_str)
        result = await PaymentService.create_payment(user_id, plan)

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=result["confirmation_url"])],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="subscription_menu")],
        ])

        await callback.message.edit_text(
            f"💳 <b>Оплата подписки {plan.value.upper()}</b>\n\n"
            f"Сумма: <b>{result['amount']:.0f}₽</b>\n\n"
            f"Нажмите кнопку ниже для оплаты через ЮKassa:",
            reply_markup=kb,
        )
    except Exception as e:
        logger.error(f"Payment creation error: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при создании платежа. Попробуйте позже."
        )

    await callback.answer()