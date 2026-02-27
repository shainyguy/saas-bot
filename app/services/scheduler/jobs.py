# app/services/scheduler/jobs.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone

scheduler = AsyncIOScheduler(timezone="UTC")


async def check_expired_subscriptions():
    try:
        from app.db.database import Database
        from app.db.repositories.subscription_repo import SubscriptionRepository
        async with Database.session() as session:
            repo = SubscriptionRepository(session)
            expired_users = await repo.check_and_expire()
            if expired_users:
                from app.bot.loader import bot
                for user_id in expired_users:
                    try:
                        await bot.send_message(
                            chat_id=user_id,
                            text="Your subscription has expired. /subscribe to renew.",
                        )
                    except Exception:
                        pass
    except Exception as e:
        print(f"[SCHEDULER] sub check error: {e}", flush=True)


async def process_scheduled_posts():
    try:
        from app.db.database import Database
        from app.db.repositories.post_repo import PostRepository
        from app.bot.loader import bot
        from app.services.automation.autopost import AutoPostService
        count = await AutoPostService.publish_scheduled_posts(bot)
        if count:
            print(f"[SCHEDULER] Published {count} posts", flush=True)
    except Exception as e:
        # Тихо игнорируем если таблиц нет
        if "does not exist" not in str(e):
            print(f"[SCHEDULER] posts error: {e}", flush=True)


async def process_pending_tasks():
    try:
        from app.db.database import Database
        from app.db.repositories.task_repo import TaskRepository
        async with Database.session() as session:
            repo = TaskRepository(session)
            tasks = await repo.get_pending_tasks(limit=20)
            for task in tasks:
                try:
                    await repo.mark_running(task.id)
                    await repo.mark_completed(task.id, {"note": "processed"})
                except Exception as e:
                    await repo.mark_failed(task.id, str(e))
    except Exception as e:
        if "does not exist" not in str(e):
            print(f"[SCHEDULER] tasks error: {e}", flush=True)


async def collect_analytics():
    try:
        from app.services.cache.redis_cache import RedisCache
        from app.db.database import Database
        from sqlalchemy import func, select, text

        async with Database.session() as session:
            try:
                result = await session.execute(text("SELECT COUNT(*) FROM users"))
                users_count = result.scalar() or 0
            except Exception:
                users_count = 0

        await RedisCache.set("analytics:dashboard", {
            "total_users": users_count,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ttl=3700)
    except Exception as e:
        if "does not exist" not in str(e):
            print(f"[SCHEDULER] analytics error: {e}", flush=True)


def setup_scheduler():
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
    print("[SCHEDULER] All jobs registered", flush=True)
