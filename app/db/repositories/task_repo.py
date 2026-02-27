# app/db/repositories/task_repo.py
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from uuid import UUID

from app.db.models import Task, TaskStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        title: str,
        task_type: str,
        description: str | None = None,
        cron_expression: str | None = None,
        payload: dict | None = None,
        next_run_at: datetime | None = None,
    ) -> Task:
        task = Task(
            user_id=user_id,
            title=title,
            task_type=task_type,
            description=description,
            cron_expression=cron_expression,
            is_recurring=bool(cron_expression),
            payload=payload or {},
            next_run_at=next_run_at,
        )
        self.session.add(task)
        await self.session.flush()
        logger.info(f"Task created: {task.id} for user {user_id}")
        return task

    async def get_pending_tasks(self, limit: int = 100) -> list[Task]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(Task)
            .where(
                Task.status == TaskStatus.PENDING,
                Task.next_run_at <= now,
            )
            .order_by(Task.next_run_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_running(self, task_id: UUID) -> None:
        await self.session.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(status=TaskStatus.RUNNING, last_run_at=datetime.now(timezone.utc))
        )

    async def mark_completed(self, task_id: UUID, result: dict | None = None) -> None:
        await self.session.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(status=TaskStatus.COMPLETED, result=result)
        )

    async def mark_failed(self, task_id: UUID, error: str) -> None:
        stmt = select(Task).where(Task.id == task_id)
        result = await self.session.execute(stmt)
        task = result.scalar_one_or_none()
        if task:
            task.retry_count += 1
            if task.retry_count >= task.max_retries:
                task.status = TaskStatus.FAILED
            else:
                task.status = TaskStatus.PENDING
            task.result = {"error": error}

    async def get_user_tasks(
        self, user_id: int, limit: int = 50, offset: int = 0
    ) -> list[Task]:
        stmt = (
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_user_tasks(self, user_id: int) -> int:
        from sqlalchemy import func
        stmt = select(func.count(Task.id)).where(Task.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0