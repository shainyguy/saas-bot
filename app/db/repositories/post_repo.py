# app/db/repositories/post_repo.py
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.db.models import Post, PostStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PostRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        content: str,
        channel_id: int | None = None,
        scheduled_at: datetime | None = None,
        platforms: list[str] | None = None,
        media_urls: list[str] | None = None,
        ab_variant: str | None = None,
        ab_group_id: UUID | None = None,
    ) -> Post:
        status = PostStatus.SCHEDULED if scheduled_at else PostStatus.DRAFT

        post = Post(
            user_id=user_id,
            channel_id=channel_id,
            content=content,
            media_urls=media_urls or [],
            status=status,
            scheduled_at=scheduled_at,
            platforms=platforms or ["telegram"],
            ab_variant=ab_variant,
            ab_group_id=ab_group_id,
        )
        self.session.add(post)
        await self.session.flush()
        return post

    async def create_ab_test(
        self, user_id: int, content_a: str, content_b: str,
        channel_id: int, scheduled_at: datetime,
    ) -> tuple[Post, Post]:
        group_id = uuid4()
        post_a = await self.create(
            user_id=user_id, content=content_a, channel_id=channel_id,
            scheduled_at=scheduled_at, ab_variant="A", ab_group_id=group_id,
        )
        post_b = await self.create(
            user_id=user_id, content=content_b, channel_id=channel_id,
            scheduled_at=scheduled_at, ab_variant="B", ab_group_id=group_id,
        )
        return post_a, post_b

    async def get_scheduled_posts(self, limit: int = 50) -> list[Post]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(Post)
            .where(Post.status == PostStatus.SCHEDULED, Post.scheduled_at <= now)
            .order_by(Post.scheduled_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_published(self, post_id: UUID, engagement: dict | None = None) -> None:
        await self.session.execute(
            update(Post)
            .where(Post.id == post_id)
            .values(
                status=PostStatus.PUBLISHED,
                published_at=datetime.now(timezone.utc),
                engagement_data=engagement or {},
            )
        )

    async def get_user_posts(
        self, user_id: int, status: PostStatus | None = None,
        limit: int = 50, offset: int = 0,
    ) -> list[Post]:
        stmt = select(Post).where(Post.user_id == user_id)
        if status:
            stmt = stmt.where(Post.status == status)
        stmt = stmt.order_by(Post.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())