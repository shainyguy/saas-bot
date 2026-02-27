# app/services/automation/autopost.py
from datetime import datetime, timezone

from aiogram import Bot

from app.db.database import Database
from app.db.repositories.post_repo import PostRepository
from app.db.models import PostStatus
from app.services.automation.crosspost import CrossPostService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AutoPostService:

    @staticmethod
    async def publish_scheduled_posts(bot: Bot) -> int:
        """Опубликовать все запланированные посты. Вернуть кол-во."""
        published = 0

        async with Database.session() as session:
            repo = PostRepository(session)
            posts = await repo.get_scheduled_posts(limit=50)

            for post in posts:
                try:
                    # Telegram
                    if "telegram" in (post.platforms or []):
                        if post.channel_id:
                            from sqlalchemy import select
                            from app.db.models import Channel
                            ch_result = await session.execute(
                                select(Channel).where(Channel.id == post.channel_id)
                            )
                            channel = ch_result.scalar_one_or_none()
                            if channel and channel.telegram_channel_id:
                                await bot.send_message(
                                    chat_id=channel.telegram_channel_id,
                                    text=post.content,
                                    parse_mode="HTML",
                                )

                    # Кросспостинг
                    platforms = post.platforms or []
                    if "vk" in platforms:
                        await CrossPostService.post_to_vk(post)
                    if "instagram" in platforms:
                        await CrossPostService.post_to_instagram(post)

                    await repo.mark_published(post.id)
                    published += 1
                    logger.info(f"Post published: {post.id}")

                except Exception as e:
                    logger.error(f"Failed to publish post {post.id}: {e}")
                    post.status = PostStatus.FAILED

        return published