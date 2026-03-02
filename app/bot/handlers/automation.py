# app/bot/handlers/automation.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from datetime import datetime, timezone

from app.bot.keyboards.inline import automation_menu_keyboard, tasks_menu_keyboard, back_keyboard
from app.db.database import Database
from app.db.repositories.post_repo import PostRepository
from app.db.repositories.task_repo import TaskRepository

router = Router()


# === States ===
class AutoPostStates(StatesGroup):
    waiting_channel = State()
    waiting_content = State()
    waiting_schedule = State()


class TaskStates(StatesGroup):
    waiting_title = State()
    waiting_type = State()


# === Меню автоматизации ===
@router.callback_query(F.data == "menu_automation")
async def menu_automation(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "⚡ <b>Автоматизация</b>\n\nВыберите действие:",
            reply_markup=automation_menu_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            "⚡ <b>Автоматизация</b>\n\nВыберите действие:",
            reply_markup=automation_menu_keyboard(),
        )
    await callback.answer()


# === Меню задач ===
@router.callback_query(F.data == "menu_tasks")
async def menu_tasks(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "📋 <b>Задачи</b>\n\nВыберите действие:",
            reply_markup=tasks_menu_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            "📋 <b>Задачи</b>\n\nВыберите действие:",
            reply_markup=tasks_menu_keyboard(),
        )
    await callback.answer()


# === Автопостинг: начало ===
@router.callback_query(F.data == "menu_autopost")
async def menu_autopost(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "📝 <b>Автопостинг</b>\n\nВыберите действие:",
            reply_markup=automation_menu_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            "📝 <b>Автопостинг</b>",
            reply_markup=automation_menu_keyboard(),
        )
    await callback.answer()


# === Создать автопост ===
@router.callback_query(F.data == "auto_newpost")
async def auto_newpost_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 <b>Новый автопост</b>\n\n"
        "Отправьте ID канала (число).\n"
        "Бот должен быть администратором канала.\n\n"
        "Отправьте /cancel для отмены."
    )
    await state.set_state(AutoPostStates.waiting_channel)
    await callback.answer()


@router.message(AutoPostStates.waiting_channel)
async def auto_newpost_channel(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=back_keyboard())
        return

    try:
        channel_id = int(message.text)
        await state.update_data(channel_id=channel_id)
        await message.answer(
            "Отправьте текст поста.\n"
            "Поддерживается HTML разметка."
        )
        await state.set_state(AutoPostStates.waiting_content)
    except (ValueError, TypeError):
        await message.answer("❌ Отправьте число (ID канала).\nИли /cancel для отмены.")


@router.message(AutoPostStates.waiting_content)
async def auto_newpost_content(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=back_keyboard())
        return

    await state.update_data(content=message.text)
    await message.answer(
        "Когда опубликовать?\n\n"
        "Формат: <code>2025-06-15 14:30</code>\n"
        "Или <code>now</code> — прямо сейчас\n"
        "Или /cancel для отмены"
    )
    await state.set_state(AutoPostStates.waiting_schedule)


@router.message(AutoPostStates.waiting_schedule)
async def auto_newpost_schedule(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=back_keyboard())
        return

    data = await state.get_data()
    channel_id = data.get("channel_id")
    content = data.get("content", "")
    await state.clear()

    text = message.text.strip().lower() if message.text else ""

    if text == "now":
        try:
            await message.bot.send_message(
                chat_id=channel_id,
                text=content,
                parse_mode="HTML",
            )
            await message.answer("✅ Пост опубликован!", reply_markup=back_keyboard())
        except Exception as e:
            await message.answer(
                f"❌ Ошибка: {e}\n\n"
                f"Убедитесь что бот — админ канала.",
                reply_markup=back_keyboard(),
            )
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
                f"📅 {scheduled_at.strftime('%d.%m.%Y %H:%M')} UTC\n"
                f"🆔 <code>{post.id}</code>",
                reply_markup=back_keyboard(),
            )
        except ValueError:
            await message.answer(
                "❌ Неверный формат.\n"
                "Используйте: <code>2025-06-15 14:30</code>",
                reply_markup=back_keyboard(),
            )
        except Exception as e:
            await message.answer(
                f"❌ Ошибка: {e}",
                reply_markup=back_keyboard(),
            )


# === Мои посты ===
@router.callback_query(F.data == "auto_myposts")
async def auto_myposts(callback: CallbackQuery):
    try:
        async with Database.session() as session:
            repo = PostRepository(session)
            posts = await repo.get_user_posts(callback.from_user.id, limit=10)

        if not posts:
            text = "📝 У вас пока нет постов."
        else:
            lines = ["📝 <b>Ваши посты:</b>\n"]
            for p in posts:
                status_icon = {
                    "draft": "📄", "scheduled": "⏳",
                    "published": "✅", "failed": "❌",
                }.get(str(p.status), "❓")

                content_preview = (p.content or "")[:50]
                lines.append(f"{status_icon} {content_preview}...")

            text = "\n".join(lines)
    except Exception as e:
        text = f"❌ Ошибка загрузки: {e}"

    try:
        await callback.message.edit_text(text, reply_markup=back_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=back_keyboard())
    await callback.answer()


# === Триггеры ===
@router.callback_query(F.data == "auto_newtrigger")
async def auto_newtrigger(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚡ <b>Триггеры</b>\n\n"
        "Триггер = если X → сделать Y\n\n"
        "Примеры:\n"
        "• Новый подписчик → отправить приветствие\n"
        "• Ключевое слово → автоответ\n"
        "• Время → отправить пост\n\n"
        "🔜 Визуальный конструктор триггеров скоро в Mini App!",
        reply_markup=back_keyboard(),
    )
    await callback.answer()


# === Автоответчик ===
@router.callback_query(F.data == "auto_responder")
async def auto_responder(callback: CallbackQuery):
    await callback.message.edit_text(
        "🤖 <b>Автоответчик</b>\n\n"
        "AI автоматически отвечает на входящие сообщения.\n\n"
        "🔜 Настройка через Mini App скоро!",
        reply_markup=back_keyboard(),
    )
    await callback.answer()


# === Список задач ===
@router.callback_query(F.data == "tasks_list")
@router.message(Command("tasks"))
async def show_tasks(event: Message | CallbackQuery):
    user_id = event.from_user.id

    try:
        async with Database.session() as session:
            repo = TaskRepository(session)
            tasks = await repo.get_user_tasks(user_id, limit=10)

        if not tasks:
            text = "📋 Нет задач. Создайте новую!"
        else:
            lines = ["📋 <b>Ваши задачи:</b>\n"]
            for t in tasks:
                icon = {
                    "pending": "⏳", "running": "🔄",
                    "completed": "✅", "failed": "❌",
                }.get(str(t.status), "❓")
                lines.append(f"{icon} <b>{t.title}</b> — {t.task_type}")
            text = "\n".join(lines)
    except Exception as e:
        text = f"❌ Ошибка: {e}"

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=back_keyboard())
        except Exception:
            await event.message.answer(text, reply_markup=back_keyboard())
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_keyboard())


# === Новая задача ===
@router.callback_query(F.data == "tasks_new")
async def tasks_new_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📋 <b>Новая задача</b>\n\n"
        "Введите название задачи.\n"
        "Или /cancel для отмены."
    )
    await state.set_state(TaskStates.waiting_title)
    await callback.answer()


@router.message(TaskStates.waiting_title)
async def tasks_new_title(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=back_keyboard())
        return

    await state.update_data(title=message.text)
    await message.answer(
        "Выберите тип задачи:\n\n"
        "• <code>autopost</code> — автопостинг\n"
        "• <code>ai_generate</code> — AI генерация\n"
        "• <code>reminder</code> — напоминание\n"
        "• <code>crosspost</code> — кросспостинг\n"
    )
    await state.set_state(TaskStates.waiting_type)


@router.message(TaskStates.waiting_type)
async def tasks_new_type(message: Message, state: FSMContext):
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=back_keyboard())
        return

    data = await state.get_data()
    task_type = (message.text or "").strip().lower()
    await state.clear()

    valid_types = ["autopost", "ai_generate", "reminder", "crosspost"]
    if task_type not in valid_types:
        await message.answer(
            f"❌ Неизвестный тип. Используйте: {', '.join(valid_types)}",
            reply_markup=back_keyboard(),
        )
        return

    try:
        async with Database.session() as session:
            repo = TaskRepository(session)
            task = await repo.create(
                user_id=message.from_user.id,
                title=data.get("title", "Без названия"),
                task_type=task_type,
                next_run_at=datetime.now(timezone.utc),
            )

        await message.answer(
            f"✅ Задача создана!\n\n"
            f"📋 {data.get('title')}\n"
            f"🔧 Тип: {task_type}\n"
            f"🆔 <code>{task.id}</code>",
            reply_markup=back_keyboard(),
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=back_keyboard())


# === Статистика ===
@router.callback_query(F.data == "menu_stats")
async def menu_stats(callback: CallbackQuery):
    user_id = callback.from_user.id

    try:
        async with Database.session() as session:
            from sqlalchemy import func, select
            from app.db.models import Post, Task

            posts_count = (await session.execute(
                select(func.count(Post.id)).where(Post.user_id == user_id)
            )).scalar() or 0

            published = (await session.execute(
                select(func.count(Post.id)).where(
                    Post.user_id == user_id,
                    Post.status == "published",
                )
            )).scalar() or 0

            tasks_count = (await session.execute(
                select(func.count(Task.id)).where(Task.user_id == user_id)
            )).scalar() or 0

        text = (
            f"📈 <b>Статистика</b>\n\n"
            f"📝 Постов: <b>{posts_count}</b>\n"
            f"✅ Опубликовано: <b>{published}</b>\n"
            f"📋 Задач: <b>{tasks_count}</b>\n"
        )
    except Exception as e:
        text = f"📈 <b>Статистика</b>\n\n❌ Ошибка: {e}"

    try:
        await callback.message.edit_text(text, reply_markup=back_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=back_keyboard())
    await callback.answer()