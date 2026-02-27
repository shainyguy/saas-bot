# app/bot/handlers/automation.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from datetime import datetime, timezone

from app.db.database import Database
from app.db.repositories.post_repo import PostRepository
from app.db.repositories.task_repo import TaskRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = Router()


class AutoPostStates(StatesGroup):
    waiting_channel = State()
    waiting_content = State()
    waiting_schedule = State()


class TaskStates(StatesGroup):
    waiting_title = State()
    waiting_type = State()
    waiting_cron = State()


@router.message(Command("autopost"))
@router.callback_query(F.data == "autopost_menu")
async def autopost_start(event: Message | CallbackQuery, state: FSMContext):
    text = (
        "📝 <b>Автопостинг</b>\n\n"
        "Отправьте ID канала (бот должен быть админом):"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text)
        await event.answer()
    else:
        await event.answer(text)
    await state.set_state(AutoPostStates.waiting_channel)


@router.message(AutoPostStates.waiting_channel)
async def autopost_channel(message: Message, state: FSMContext):
    try:
        channel_id = int(message.text)
        await state.update_data(channel_id=channel_id)
        await message.answer("Отправьте текст поста (HTML разметка поддерживается):")
        await state.set_state(AutoPostStates.waiting_content)
    except ValueError:
        await message.answer("❌ Неверный ID канала. Отправьте число:")


@router.message(AutoPostStates.waiting_content)
async def autopost_content(message: Message, state: FSMContext):
    await state.update_data(content=message.text)
    await message.answer(
        "Когда опубликовать?\n\n"
        "Отправьте дату и время в формате:\n"
        "<code>2025-01-15 14:30</code>\n\n"
        "Или <code>now</code> для немедленной публикации:"
    )
    await state.set_state(AutoPostStates.waiting_schedule)


@router.message(AutoPostStates.waiting_schedule)
async def autopost_schedule(message: Message, state: FSMContext):
    data = await state.get_data()
    channel_id = data["channel_id"]
    content = data["content"]

    if message.text.strip().lower() == "now":
        # Немедленная публикация
        try:
            await message.bot.send_message(
                chat_id=channel_id,
                text=content,
                parse_mode="HTML",
            )
            await message.answer("✅ Пост опубликован!")
        except Exception as e:
            await message.answer(f"❌ Ошибка публикации: {e}")
    else:
        try:
            scheduled_at = datetime.strptime(
                message.text.strip(), "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)

            async with Database.session() as session:
                repo = PostRepository(session)
                post = await repo.create(
                    user_id=message.from_user.id,
                    content=content,
                    scheduled_at=scheduled_at,
                    platforms=["telegram"],
                )

            await message.answer(
                f"✅ Пост запланирован!\n"
                f"📅 Дата: {scheduled_at.strftime('%d.%m.%Y %H:%M UTC')}\n"
                f"🆔 ID: <code>{post.id}</code>"
            )
        except ValueError:
            await message.answer("❌ Неверный формат даты.")

    await state.clear()


# --- Задачи ---
@router.message(Command("tasks"))
async def show_tasks(message: Message):
    async with Database.session() as session:
        repo = TaskRepository(session)
        tasks = await repo.get_user_tasks(message.from_user.id, limit=10)

    if not tasks:
        await message.answer("📋 У вас пока нет задач.\n\nСоздайте: /newtask")
        return

    lines = ["📋 <b>Ваши задачи:</b>\n"]
    for t in tasks:
        status_emoji = {
            "pending": "⏳", "running": "🔄",
            "completed": "✅", "failed": "❌",
        }.get(t.status.value, "❓")
        lines.append(
            f"{status_emoji} <b>{t.title}</b>\n"
            f"   Тип: {t.task_type} | Статус: {t.status.value}"
        )

    await message.answer("\n".join(lines))


@router.message(Command("newtask"))
async def new_task(message: Message, state: FSMContext):
    await message.answer("📝 Введите название задачи:")
    await state.set_state(TaskStates.waiting_title)


@router.message(TaskStates.waiting_title)
async def task_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer(
        "Выберите тип задачи:\n"
        "• <code>autopost</code> — автопостинг\n"
        "• <code>ai_generate</code> — AI генерация\n"
        "• <code>crosspost</code> — кросспостинг\n"
        "• <code>reminder</code> — напоминание\n"
    )
    await state.set_state(TaskStates.waiting_type)


@router.message(TaskStates.waiting_type)
async def task_type(message: Message, state: FSMContext):
    data = await state.get_data()
    task_type = message.text.strip().lower()

    async with Database.session() as session:
        repo = TaskRepository(session)
        task = await repo.create(
            user_id=message.from_user.id,
            title=data["title"],
            task_type=task_type,
            next_run_at=datetime.now(timezone.utc),
        )

    await message.answer(
        f"✅ Задача создана!\n"
        f"📋 {data['title']}\n"
        f"🔧 Тип: {task_type}\n"
        f"🆔 <code>{task.id}</code>"
    )
    await state.clear()