# examples/run_autopost.py
"""Пример запуска автопоста."""
import asyncio
from app.db.database import Database
from app.db.repositories.post_repo import PostRepository
from app.services.automation.autopost import AutoPostService
from datetime import datetime, timezone, timedelta


async def example_autopost():
    await Database.initialize()

    # Создать запланированный пост
    async with Database.session() as session:
        repo = PostRepository(session)
        post = await repo.create(
            user_id=123456789,
            content=(
                "🚀 <b>Новый пост!</b>\n\n"
                "Это автоматически опубликованный пост.\n"
                "#автопостинг #saas"
            ),
            channel_id=1,
            scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            platforms=["telegram", "vk"],
        )
        print(f"Post scheduled: {post.id}")

    # Запустить публикацию (нужен bot instance)
    # from app.bot.loader import bot
    # count = await AutoPostService.publish_scheduled_posts(bot)
    # print(f"Published: {count}")

    await Database.close()


if __name__ == "__main__":
    asyncio.run(example_autopost())