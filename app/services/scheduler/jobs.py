# app/services/scheduler/jobs.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone

from app.db.database import Database
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.task_repo import TaskRepository
from app.services.automation.autopost import AutoPostService
from app.services.cache.redis_cache import RedisCache
from app.utils.logger import get_logger

logger = get_logger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


async def check_expired_subscriptions():
    """Проверка истёкших подписок каждые 5 минут."""
    try:
        async with Database.session() as session:
            repo = SubscriptionRepository(session)
            expired_users = await repo.check_and_expire()

            if expired_users:
                from app.bot.loader import bot
                for user_id in expired_users:
                    try:
                        await bot.send_message(
                            chat_id=user_id,
                            text=(
                                "⚠️ <b>Ваша подписка истекла</b>\n\n"
                                "Функции ограничены до бесплатного плана.\n"
                                "Продлите подписку: /subscribe"
                            ),
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass

                # Очистить кэш подписок
                for uid in expired_users:
                    await RedisCache.delete(f"sub:{uid}")

    except Exception as e:
        logger.error(f"Subscription check error: {e}")


async def process_scheduled_posts():
    """Публикация запланированных постов каждую минуту."""
    try:
        from app.bot.loader import bot
        count = await AutoPostService.publish_scheduled_posts(bot)
        if count:
            logger.info(f"Published {count} scheduled posts")
    except Exception as e:
        logger.error(f"Scheduled posts error: {e}")


async def process_pending_tasks():
    """Обработка задач из очереди каждые 30 секунд."""
    try:
        async with Database.session() as session:
            repo = TaskRepository(session)
            tasks = await repo.get_pending_tasks(limit=20)

            for task in tasks:
                try:
                    await repo.mark_running(task.id)

                    # Диспатч по типу задачи
                    if task.task_type == "autopost":
                        from app.bot.loader import bot
                        await AutoPostService.publish_scheduled_posts(bot)
                    elif task.task_type == "ai_generate":
                        from app.services.ai.gigachat import GigaChatService
                        result = await GigaChatService.generate_post(
                            topic=task.payload.get("topic", ""),
                            user_id=task.user_id,
                        )
                        await repo.mark_completed(task.id, {"result": result})
                    elif task.task_type == "crosspost":
                        pass  # Handled in autopost
                    else:
                        await repo.mark_completed(task.id, {"note": "no handler"})

                except Exception as e:
                    await repo.mark_failed(task.id, str(e))
                    logger.error(f"Task {task.id} failed: {e}")

    except Exception as e:
        logger.error(f"Task processing error: {e}")


async def collect_analytics():
    """Сбор аналитики каждый час."""
    try:
        async with Database.session() as session:
            from sqlalchemy import func, select
            from app.db.models import User, Subscription, Post

            # Считаем метрики
            users_count = (await session.execute(
                select(func.count(User.id))
            )).scalar() or 0

            active_subs = (await session.execute(
                select(func.count(Subscription.id))
                .where(Subscription.status == "active")
            )).scalar() or 0

            posts_today = (await session.execute(
                select(func.count(Post.id))
                .where(Post.published_at >= datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0
                ))
            )).scalar() or 0

            await RedisCache.set("analytics:dashboard", {
                "total_users": users_count,
                "active_subscriptions": active_subs,
                "posts_today": posts_today,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, ttl=3700)

    except Exception as e:
        logger.error(f"Analytics collection error: {e}")


def setup_scheduler():
    """Настроить все периодические задачи."""
    scheduler.add_job(
        check_expired_subscriptions,
        IntervalTrigger(minutes=5),
        id="check_subscriptions",
        replace_existing=True,
    )
    scheduler.add_job(
        process_scheduled_posts,
        IntervalTrigger(minutes=1),
        id="scheduled_posts",
        replace_existing=True,
    )
    scheduler.add_job(
        process_pending_tasks,
        IntervalTrigger(seconds=30),
        id="pending_tasks",
        replace_existing=True,
    )
    scheduler.add_job(
        collect_analytics,
        IntervalTrigger(hours=1),
        id="collect_analytics",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started with all jobs")