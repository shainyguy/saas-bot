# app/bot/handlers/ai_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.bot.keyboards.inline import ai_menu_keyboard, back_keyboard

router = Router()


class AIStates(StatesGroup):
    waiting_topic = State()
    waiting_rewrite = State()
    waiting_comment = State()
    waiting_abtest = State()
    waiting_funnel_niche = State()
    waiting_funnel_goal = State()


@router.callback_query(F.data == "menu_ai")
async def menu_ai(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "🤖 <b>AI-инструменты</b>\n\nВыберите функцию:",
            reply_markup=ai_menu_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            "🤖 <b>AI-инструменты</b>\n\nВыберите функцию:",
            reply_markup=ai_menu_keyboard(),
        )
    await callback.answer()


# === Генерация поста ===
@router.callback_query(F.data == "ai_post")
async def ai_post_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✍️ <b>Генерация поста</b>\n\n"
        "Напишите тему или описание.\n"
        "Или /cancel для отмены."
    )
    await state.set_state(AIStates.waiting_topic)
    await callback.answer()


@router.message(AIStates.waiting_topic)
async def ai_post_process(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=back_keyboard())
        return

    topic = message.text or ""
    await state.clear()
    wait_msg = await message.answer("⏳ Генерирую пост...")

    try:
        from app.services.ai.gigachat import GigaChatService
        result = await GigaChatService.generate_post(
            topic=topic,
            user_id=message.from_user.id,
        )
        await wait_msg.edit_text(
            f"✅ <b>Готово!</b>\n\n{result}",
            reply_markup=back_keyboard(),
        )
    except Exception as e:
        await wait_msg.edit_text(
            f"❌ Ошибка генерации: {str(e)[:200]}\n\n"
            f"Проверьте GIGACHAT_API_KEY.",
            reply_markup=back_keyboard(),
        )


# === Рерайт ===
@router.callback_query(F.data == "ai_rewrite")
async def ai_rewrite_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔄 <b>Рерайт</b>\n\n"
        "Отправьте текст для переработки.\n"
        "Или /cancel для отмены."
    )
    await state.set_state(AIStates.waiting_rewrite)
    await callback.answer()


@router.message(AIStates.waiting_rewrite)
async def ai_rewrite_process(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=back_keyboard())
        return

    await state.clear()
    wait_msg = await message.answer("⏳ Переписываю...")

    try:
        from app.services.ai.gigachat import GigaChatService
        result = await GigaChatService.rewrite_text(
            text=message.text or "",
            user_id=message.from_user.id,
        )
        await wait_msg.edit_text(
            f"✅ <b>Результат:</b>\n\n{result}",
            reply_markup=back_keyboard(),
        )
    except Exception as e:
        await wait_msg.edit_text(
            f"❌ Ошибка: {str(e)[:200]}",
            reply_markup=back_keyboard(),
        )


# === Комментарий ===
@router.callback_query(F.data == "ai_comment")
async def ai_comment_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "💬 <b>Генерация комментария</b>\n\n"
        "Отправьте текст поста.\n"
        "Или /cancel для отмены."
    )
    await state.set_state(AIStates.waiting_comment)
    await callback.answer()


@router.message(AIStates.waiting_comment)
async def ai_comment_process(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=back_keyboard())
        return

    await state.clear()
    wait_msg = await message.answer("⏳ Генерирую...")

    try:
        from app.services.ai.gigachat import GigaChatService
        result = await GigaChatService.generate_comment(
            post_text=message.text or "",
            user_id=message.from_user.id,
        )
        await wait_msg.edit_text(
            f"💬 <b>Комментарий:</b>\n\n{result}",
            reply_markup=back_keyboard(),
        )
    except Exception as e:
        await wait_msg.edit_text(
            f"❌ Ошибка: {str(e)[:200]}",
            reply_markup=back_keyboard(),
        )


# === A/B тест ===
@router.callback_query(F.data == "ai_abtest")
async def ai_abtest_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔀 <b>A/B тестирование</b>\n\n"
        "Отправьте текст поста — создам 2 варианта.\n"
        "Или /cancel для отмены."
    )
    await state.set_state(AIStates.waiting_abtest)
    await callback.answer()


@router.message(AIStates.waiting_abtest)
async def ai_abtest_process(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=back_keyboard())
        return

    await state.clear()
    wait_msg = await message.answer("⏳ Создаю A/B варианты...")

    try:
        from app.services.ai.gigachat import GigaChatService
        va, vb = await GigaChatService.ab_rewrite(
            text=message.text or "",
            user_id=message.from_user.id,
        )
        text = (
            f"🔀 <b>A/B Варианты:</b>\n\n"
            f"<b>── A ──</b>\n{va[:1500]}\n\n"
            f"<b>── B ──</b>\n{vb[:1500]}"
        )
        if len(text) > 4000:
            text = text[:4000] + "..."
        await wait_msg.edit_text(text, reply_markup=back_keyboard())
    except Exception as e:
        await wait_msg.edit_text(
            f"❌ Ошибка: {str(e)[:200]}",
            reply_markup=back_keyboard(),
        )


# === Воронка ===
@router.callback_query(F.data == "ai_funnel")
async def ai_funnel_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🎯 <b>AI-воронка</b>\n\n"
        "Укажите нишу бизнеса.\n"
        "Или /cancel для отмены."
    )
    await state.set_state(AIStates.waiting_funnel_niche)
    await callback.answer()


@router.message(AIStates.waiting_funnel_niche)
async def ai_funnel_niche(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=back_keyboard())
        return

    await state.update_data(niche=message.text)
    await message.answer("Укажите цель воронки (например: продажа курса):")
    await state.set_state(AIStates.waiting_funnel_goal)


@router.message(AIStates.waiting_funnel_goal)
async def ai_funnel_goal(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=back_keyboard())
        return

    data = await state.get_data()
    niche = data.get("niche", "")
    goal = message.text or ""
    await state.clear()

    wait_msg = await message.answer("⏳ Строю воронку...")

    try:
        from app.services.ai.gigachat import GigaChatService
        result = await GigaChatService.build_funnel_advice(
            niche=niche,
            goal=goal,
            user_id=message.from_user.id,
        )
        # Разбить длинный ответ
        if len(result) > 4000:
            await wait_msg.edit_text(result[:4000])
            for i in range(4000, len(result), 4000):
                await message.answer(result[i:i + 4000])
        else:
            await wait_msg.edit_text(
                f"🎯 <b>Воронка:</b>\n\n{result}",
                reply_markup=back_keyboard(),
            )
    except Exception as e:
        await wait_msg.edit_text(
            f"❌ Ошибка: {str(e)[:200]}",
            reply_markup=back_keyboard(),
        )