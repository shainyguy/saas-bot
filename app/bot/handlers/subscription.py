# app/bot/handlers/subscription.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from app.bot.keyboards.inline import subscription_keyboard, back_keyboard
from app.config import PlanType, settings
from app.db.database import Database
from app.db.repositories.subscription_repo import SubscriptionRepository

router = Router()

PLAN_MAP = {
    "pay_starter": PlanType.STARTER,
    "pay_pro": PlanType.PRO,
    "pay_business": PlanType.BUSINESS,
    "pay_weekly": PlanType.WEEKLY,
}


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    text = await _get_subscription_text(message.from_user.id)
    await message.answer(text, reply_markup=subscription_keyboard())


@router.callback_query(F.data == "menu_subscription")
async def menu_subscription(callback: CallbackQuery):
    text = await _get_subscription_text(callback.from_user.id)
    try:
        await callback.message.edit_text(text, reply_markup=subscription_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=subscription_keyboard())
    await callback.answer()


async def _get_subscription_text(user_id: int) -> str:
    try:
        async with Database.session() as session:
            sub_repo = SubscriptionRepository(session)
            current_sub = await sub_repo.get_active(user_id)

        if current_sub:
            plan_name = str(current_sub.plan or "free").upper()
            status = str(current_sub.status or "unknown")
            if current_sub.expires_at:
                expires = current_sub.expires_at.strftime("%d.%m.%Y %H:%M")
            else:
                expires = "∞"

            return (
                f"💎 <b>Ваша подписка</b>\n\n"
                f"📋 План: <b>{plan_name}</b>\n"
                f"📊 Статус: <b>{status}</b>\n"
                f"📅 До: <b>{expires}</b>\n\n"
                f"Выберите план:"
            )
    except Exception as e:
        print(f"[SUB] Error getting sub: {e}", flush=True)

    return (
        "💎 <b>Тарифные планы</b>\n\n"
        "🟢 <b>Starter</b> — 490₽/мес\n"
        "  • 3 канала, 50 задач, 100 AI/день\n\n"
        "🔵 <b>Pro</b> — 1 490₽/мес\n"
        "  • 10 каналов, кросспостинг, A/B\n\n"
        "🟣 <b>Business</b> — 3 990₽/мес\n"
        "  • Без лимитов\n\n"
        "⚡ <b>Неделя</b> — 390₽\n"
    )


@router.callback_query(F.data.in_({"pay_starter", "pay_pro", "pay_business", "pay_weekly"}))
async def process_pay(callback: CallbackQuery):
    plan = PLAN_MAP.get(callback.data)
    if not plan:
        await callback.answer("Неизвестный план", show_alert=True)
        return

    user_id = callback.from_user.id

    # Админ — бесплатно
    if user_id in settings.admin_ids_set:
        try:
            async with Database.session() as session:
                sub_repo = SubscriptionRepository(session)
                await sub_repo.activate(user_id, plan, duration_days=365)

            await callback.message.edit_text(
                f"👑 Подписка <b>{plan.value.upper()}</b> активирована (Admin).",
                reply_markup=back_keyboard(),
            )
        except Exception as e:
            await callback.message.edit_text(
                f"❌ Ошибка: {e}",
                reply_markup=back_keyboard(),
            )
        await callback.answer("Активировано!")
        return

    # Обычный пользователь — ЮKassa
    try:
        from app.services.payments.yukassa import PaymentService
        result = await PaymentService.create_payment(user_id, plan)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=result["confirmation_url"])],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_subscription")],
        ])

        await callback.message.edit_text(
            f"💳 <b>Оплата {plan.value.upper()}</b>\n\n"
            f"Сумма: <b>{result['amount']:.0f}₽</b>\n\n"
            f"Нажмите кнопку для оплаты:",
            reply_markup=kb,
        )
    except Exception as e:
        print(f"[PAY] Error: {e}", flush=True)
        await callback.message.edit_text(
            f"❌ Ошибка создания платежа.\n\n"
            f"Убедитесь что YUKASSA настроена.\n"
            f"<code>{str(e)[:200]}</code>",
            reply_markup=back_keyboard(),
        )

    await callback.answer()