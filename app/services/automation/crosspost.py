# app/services/automation/crosspost.py
import httpx

from app.config import settings
from app.db.models import Post
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CrossPostService:

    @staticmethod
    async def post_to_vk(post: Post) -> dict | None:
        if not settings.VK_ACCESS_TOKEN:
            logger.warning("VK token not configured")
            return None

        try:
            # Получить vk_group_id из channel
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.vk.com/method/wall.post",
                    data={
                        "access_token": settings.VK_ACCESS_TOKEN,
                        "v": "5.199",
                        "owner_id": f"-{post.metadata_.get('vk_group_id', '')}",
                        "message": post.content,
                        "from_group": 1,
                    },
                )
                data = response.json()
                if "error" in data:
                    logger.error(f"VK API error: {data['error']}")
                    return None
                logger.info(f"Posted to VK: {data}")
                return data
        except Exception as e:
            logger.error(f"VK crosspost failed: {e}")
            return None

    @staticmethod
    async def post_to_instagram(post: Post) -> dict | None:
        if not settings.INSTAGRAM_ACCESS_TOKEN:
            logger.warning("Instagram token not configured")
            return None

        try:
            ig_user_id = post.metadata_.get("instagram_account_id", "")
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Шаг 1: создать media container
                media_urls = post.media_urls or []
                if media_urls:
                    create_resp = await client.post(
                        f"https://graph.facebook.com/v18.0/{ig_user_id}/media",
                        data={
                            "image_url": media_urls[0],
                            "caption": post.content,
                            "access_token": settings.INSTAGRAM_ACCESS_TOKEN,
                        },
                    )
                    container = create_resp.json()
                    container_id = container.get("id")

                    if container_id:
                        # Шаг 2: publish
                        pub_resp = await client.post(
                            f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish",
                            data={
                                "creation_id": container_id,
                                "access_token": settings.INSTAGRAM_ACCESS_TOKEN,
                            },
                        )
                        result = pub_resp.json()
                        logger.info(f"Posted to Instagram: {result}")
                        return result

        except Exception as e:
            logger.error(f"Instagram crosspost failed: {e}")
            return None