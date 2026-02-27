# examples/create_task.py
"""Пример создания задачи."""
import asyncio
from datetime import datetime, timezone, timedelta
from app.db.database import Database
from app.db.repositories.task_repo import TaskRepository


async def example_create_task():
    await Database.initialize()

    async with Database.session() as session:
        repo = TaskRepository(session)

        # Одноразовая задача
        task = await repo.create(
            user_id=123456789,
            title="Опубликовать еженедельный дайджест",
            task_type="autopost",
            payload={
                "channel_id": -1001234567890,
                "content": "📰 Еженедельный дайджест...",
            },
            next_run_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        print(f"Task created: {task.id}")

        # Рекурсивная задача (CRON)
        cron_task = await repo.create(
            user_id=123456789,
            title="Ежедневный отчёт",
            task_type="ai_generate",
            cron_expression="0 9 * * *",  # Каждый день в 9:00
            payload={"topic": "ежедневный отчёт по аналитике"},
            next_run_at=datetime.now(timezone.utc),
        )
        print(f"Cron task created: {cron_task.id}")

    await Database.close()


if __name__ == "__main__":
    asyncio.run(example_create_task())