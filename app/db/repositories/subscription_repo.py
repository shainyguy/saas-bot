# app/db/repositories/subscription_repo.py
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from uuid import UUID

from app.db.models import Subscription, SubscriptionStatus
from app.config import PlanType, PlanLimits, settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_trial(self, user_id: int) -> Subscription:
        now = datetime.now(timezone.utc)
        trial_end = now + timedelta(days=settings.TRIAL_DAYS)

        sub = Subscription(
            user_id=user_id,
            plan=PlanType.STARTER.value,
            status=SubscriptionStatus.TRIAL,
            started_at=now,
            trial_ends_at=trial_end,
            expires_at=trial_end,
        )
        self.session.add(sub)
        await self.session.flush()
        logger.info(f"Trial subscription created for user {user_id}")
        return sub

    async def get_active(self, user_id: int) -> Subscription | None:
        stmt = (
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIAL,
                ]),
            )
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def activate(
        self,
        user_id: int,
        plan: PlanType,
        duration_days: int = 30,
        yukassa_id: str | None = None,
    ) -> Subscription:
        # Деактивировать старые
        await self.session.execute(
            update(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIAL,
                ]),
            )
            .values(status=SubscriptionStatus.EXPIRED)
        )

        now = datetime.now(timezone.utc)
        sub = Subscription(
            user_id=user_id,
            plan=plan.value,
            status=SubscriptionStatus.ACTIVE,
            started_at=now,
            expires_at=now + timedelta(days=duration_days),
            yukassa_subscription_id=yukassa_id,
        )
        self.session.add(sub)
        await self.session.flush()
        logger.info(f"Subscription activated: user={user_id}, plan={plan.value}")
        return sub

    async def check_and_expire(self) -> list[int]:
        """Проверить и деактивировать истекшие подписки. Вернуть user_ids."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Subscription)
            .where(
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIAL,
                ]),
                Subscription.expires_at <= now,
            )
        )
        result = await self.session.execute(stmt)
        expired = result.scalars().all()

        user_ids = []
        for sub in expired:
            sub.status = SubscriptionStatus.EXPIRED
            user_ids.append(sub.user_id)

        if user_ids:
            logger.info(f"Expired {len(user_ids)} subscriptions")
        return user_ids

    async def get_plan_limits(self, user_id: int) -> dict:
        sub = await self.get_active(user_id)
        if not sub:
            return PlanLimits.get(PlanType.FREE)

        try:
            plan = PlanType(sub.plan)
        except ValueError:
            plan = PlanType.FREE

        return PlanLimits.get(plan)

    async def get_user_plan(self, user_id: int) -> PlanType:
        sub = await self.get_active(user_id)
        if not sub:
            return PlanType.FREE
        try:
            return PlanType(sub.plan)
        except ValueError:
            return PlanType.FREE