# app/bot/handlers/ai_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.bot.keyboards.inline import ai_menu_keyboard, confirm_keyboard
from app.services.ai.gigachat import GigaChatService
from app.db.database import Database
from app.db.repositories.user_repo import UserRepository
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.services.cache.redis_cache import RedisCache
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


class AIStates(StatesGroup):
    waiting_topic = State()
    waiting_rewrite_text = State()
    waiting_comment_text = State()
    waiting_funnel_niche = State()
    waiting_funnel_goal = State()
    waiting_abtest_text = State()


@router.callback_query(F.data == "ai_menu")
async def ai_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🤖 <b>AI-инструменты</b>\n\nВыберите функцию:",
        reply_markup=ai_menu_keyboard(),
    )
    await callback.answer()


async def _check_ai_limit(user_id: int) -> tuple[bool, int]:
    """Проверить лимит AI-запросов. Возвращает (allowed, remaining)."""
    async with Database.session() as session:
        sub_repo = SubscriptionRepository(session)
        limits = await sub_repo.get_plan_limits(user_id)

    max_requests = limits.get("ai_requests_daily", 10)
    if max_requests == -1:
        return True, 999

    key = f"ai_count:{user_id}"
    current = await RedisCache.increment(key, ttl=86400)
    remaining = max(0, max_requests - current)
    return current <= max_requests, remaining


# --- Генерация поста ---
@router.callback_query(F.data == "ai:generate_post")
async def ai_generate_start(callback: CallbackQuery, state: FSMContext):
    allowed, remaining = await _check_ai_limit(callback.from_user.id)
    if not allowed:
        await callback.answer("⚠️ Лимит AI-запросов исчерпан!", show_alert=True)
        return

    await callback.message.edit_text(
        f"✍️ <b>Генерация поста</b>\n\n"
        f"Напишите тему или описание поста.\n"
        f"Осталось запросов: <b>{remaining}</b>",
    )
    await state.set_state(AIStates.waiting_topic)
    await callback.answer()


@router.message(AIStates.waiting_topic)
async def ai_generate_process(message: Message, state: FSMContext):
    topic = message.text
    wait_msg = await message.answer("⏳ Генерирую пост...")

    try:
        result = await GigaChatService.generate_post(
            topic=topic,
            user_id=message.from_user.id,
        )
        await wait_msg.edit_text(
            f"✅ <b>Готово!</b>\n\n{result}\n\n"
            f"<i>Тема: {topic}</i>",
            reply_markup=confirm_keyboard("save_post"),
        )
        await state.update_data(generated_post=result)
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        await wait_msg.edit_text("❌ Ошибка генерации. Попробуйте другую тему.")

    await state.clear()


# --- Рерайт ---
@router.callback_query(F.data == "ai:rewrite")
async def ai_rewrite_start(callback: CallbackQuery, state: FSMContext):
    allowed, _ = await _check_ai_limit(callback.from_user.id)
    if not allowed:
        await callback.answer("⚠️ Лимит AI-запросов исчерпан!", show_alert=True)
        return

    await callback.message.edit_text(
        "🔄 <b>Рерайт текста</b>\n\nОтправьте текст для переработки:",
    )
    await state.set_state(AIStates.waiting_rewrite_text)
    await callback.answer()


@router.message(AIStates.waiting_rewrite_text)
async def ai_rewrite_process(message: Message, state: FSMContext):
    text = message.text
    wait_msg = await message.answer("⏳ Переписываю...")

    try:
        result = await GigaChatService.rewrite_text(
            text=text, user_id=message.from_user.id
        )
        await wait_msg.edit_text(f"✅ <b>Результат:</b>\n\n{result}")
    except Exception as e:
        logger.error(f"Rewrite error: {e}")
        await wait_msg.edit_text("❌ Ошибка. Попробуйте позже.")

    await state.clear()


# --- Генерация комментария ---
@router.callback_query(F.data == "ai:comment")
async def ai_comment_start(callback: CallbackQuery, state: FSMContext):
    allowed, _ = await _check_ai_limit(callback.from_user.id)
    if not allowed:
        await callback.answer("⚠️ Лимит исчерпан!", show_alert=True)
        return

    await callback.message.edit_text(
        "💬 <b>Генерация комментария</b>\n\n"
        "Отправьте текст поста, к которому нужен комментарий:",
    )
    await state.set_state(AIStates.waiting_comment_text)
    await callback.answer()


@router.message(AIStates.waiting_comment_text)
async def ai_comment_process(message: Message, state: FSMContext):
    wait_msg = await message.answer("⏳ Генерирую комментарий...")

    try:
        result = await GigaChatService.generate_comment(
            post_text=message.text, user_id=message.from_user.id
        )
        await wait_msg.edit_text(f"💬 <b>Комментарий:</b>\n\n{result}")
    except Exception as e:
        await wait_msg.edit_text("❌ Ошибка.")

    await state.clear()


# --- A/B тест ---
@router.callback_query(F.data == "ai:abtest")
async def ai_abtest_start(callback: CallbackQuery, state: FSMContext):
    allowed, _ = await _check_ai_limit(callback.from_user.id)
    if not allowed:
        await callback.answer("⚠️ Лимит исчерпан!", show_alert=True)
        return

    await callback.message.edit_text(
        "🔀 <b>A/B тестирование</b>\n\n"
        "Отправьте текст поста. Я создам два варианта для тестирования:",
    )
    await state.set_state(AIStates.waiting_abtest_text)
    await callback.answer()


@router.message(AIStates.waiting_abtest_text)
async def ai_abtest_process(message: Message, state: FSMContext):
    wait_msg = await message.answer("⏳ Создаю варианты A/B...")

    try:
        variant_a, variant_b = await GigaChatService.ab_rewrite(
            text=message.text, user_id=message.from_user.id
        )
        await wait_msg.edit_text(
            f"🔀 <b>A/B Варианты:</b>\n\n"
            f"<b>── Вариант A ──</b>\n{variant_a}\n\n"
            f"<b>── Вариант B ──</b>\n{variant_b}"
        )
    except Exception as e:
        await wait_msg.edit_text("❌ Ошибка A/B генерации.")

    await state.clear()


# --- Построение воронки ---
@router.callback_query(F.data == "ai:funnel")
async def ai_funnel_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🎯 <b>AI-ассистент воронки</b>\n\nУкажите нишу бизнеса:",
    )
    await state.set_state(AIStates.waiting_funnel_niche)
    await callback.answer()


@router.message(AIStates.waiting_funnel_niche)
async def ai_funnel_niche(message: Message, state: FSMContext):
    await state.update_data(funnel_niche=message.text)
    await message.answer("Теперь укажите цель воронки (например: 'продажа курса'):")
    await state.set_state(AIStates.waiting_funnel_goal)


@router.message(AIStates.waiting_funnel_goal)
async def ai_funnel_goal(message: Message, state: FSMContext):
    data = await state.get_data()
    niche = data.get("funnel_niche", "")
    goal = message.text
    wait_msg = await message.answer("⏳ Строю воронку...")

    try:
        result = await GigaChatService.build_funnel_advice(
            niche=niche, goal=goal, user_id=message.from_user.id
        )
        # Длинный ответ — разбить если надо
        if len(result) > 4000:
            for i in range(0, len(result), 4000):
                await message.answer(result[i:i+4000])
            await wait_msg.delete()
        else:
            await wait_msg.edit_text(f"🎯 <b>Воронка:</b>\n\n{result}")
    except Exception as e:
        await wait_msg.edit_text("❌ Ошибка.")

    await state.clear()