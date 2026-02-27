# examples/create_subscription.py
"""Пример создания подписки."""
import asyncio
from app.db.database import Database
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.config import PlanType


async def example_create_subscription():
    await Database.initialize()

    async with Database.session() as session:
        repo = SubscriptionRepository(session)

        # Создать trial
        trial = await repo.create_trial(user_id=123456789)
        print(f"Trial created: {trial.id}, expires: {trial.expires_at}")

        # Активировать платную подписку
        sub = await repo.activate(
            user_id=123456789,
            plan=PlanType.PRO,
            duration_days=30,
        )
        print(f"Pro activated: {sub.id}, plan: {sub.plan}")

        # Проверить лимиты
        limits = await repo.get_plan_limits(123456789)
        print(f"Limits: {limits}")

    await Database.close()


if __name__ == "__main__":
    asyncio.run(example_create_subscription())