# app/services/automation/autoresponder.py
from app.services.ai.gigachat import GigaChatService
from app.services.cache.redis_cache import RedisCache
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AutoResponder:
    """AI-автоответчик для входящих сообщений."""

    @staticmethod
    async def generate_reply(
        incoming_text: str,
        user_id: int,
        context: dict | None = None,
    ) -> str | None:
        """Сгенерировать автоматический ответ на входящее сообщение."""
        # Проверить rate limit
        allowed = await RedisCache.get_rate_limit(
            user_id, "autoresponder", limit=30, window=3600
        )
        if not allowed:
            return None

        system_prompt = (
            "Ты — вежливый и профессиональный ассистент компании. "
            "Отвечай кратко, по делу. Если не знаешь ответ — "
            "предложи связаться с менеджером."
        )

        if context and context.get("custom_prompt"):
            system_prompt = context["custom_prompt"]

        try:
            response = await GigaChatService._request(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": incoming_text},
                ],
                max_tokens=512,
                temperature=0.5,
            )
            return response
        except Exception as e:
            logger.error(f"Autoresponder error: {e}")
            return None