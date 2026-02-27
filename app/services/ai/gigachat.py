# app/services/ai/gigachat.py
import httpx
import uuid
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.db.database import Database
from app.db.models import AuditLog
from app.services.cache.redis_cache import RedisCache
from app.utils.logger import get_logger

logger = get_logger(__name__)

GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1"


class GigaChatService:
    _token: str | None = None
    _token_expires: datetime | None = None

    @classmethod
    async def _get_token(cls) -> str:
        """Получить/обновить OAuth токен GigaChat."""
        now = datetime.now(timezone.utc)
        if cls._token and cls._token_expires and now < cls._token_expires:
            return cls._token

        # Проверить кэш
        cached = await RedisCache.get("gigachat:token")
        if cached:
            cls._token = cached["token"]
            cls._token_expires = datetime.fromisoformat(cached["expires"])
            if now < cls._token_expires:
                return cls._token

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                GIGACHAT_AUTH_URL,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "RqUID": str(uuid.uuid4()),
                    "Authorization": f"Basic {settings.GIGACHAT_API_KEY}",
                },
                data={"scope": settings.GIGACHAT_SCOPE},
            )
            response.raise_for_status()
            data = response.json()

        cls._token = data["access_token"]
        expires_at = data.get("expires_at", 0)
        cls._token_expires = datetime.fromtimestamp(
            expires_at / 1000, tz=timezone.utc
        )

        await RedisCache.set(
            "gigachat:token",
            {"token": cls._token, "expires": cls._token_expires.isoformat()},
            ttl=1700,
        )

        logger.info("GigaChat token refreshed")
        return cls._token

    @classmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _request(cls, messages: list[dict], **kwargs) -> str:
        token = await cls._get_token()

        async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
            response = await client.post(
                f"{GIGACHAT_API_URL}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                json={
                    "model": kwargs.get("model", "GigaChat"),
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.7),
                    "max_tokens": kwargs.get("max_tokens", 2048),
                },
            )
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"]

    @classmethod
    async def generate_post(
        cls, topic: str, style: str = "информативный",
        platform: str = "telegram", user_id: int | None = None,
    ) -> str:
        prompt = (
            f"Напиши пост для {platform} на тему: «{topic}».\n"
            f"Стиль: {style}.\n"
            f"Требования:\n"
            f"- Цепляющий заголовок\n"
            f"- Структурированный текст с эмодзи\n"
            f"- Призыв к действию в конце\n"
            f"- Длина 500-1500 символов\n"
            f"- Хэштеги в конце\n"
        )

        result = await cls._request([
            {"role": "system", "content": "Ты — профессиональный SMM-копирайтер."},
            {"role": "user", "content": prompt},
        ])

        if user_id:
            await cls._log_request(user_id, "generate_post", prompt, result)

        return result

    @classmethod
    async def rewrite_text(
        cls, text: str, style: str = "улучшенный",
        platform: str | None = None, user_id: int | None = None,
    ) -> str:
        platform_hint = f" для платформы {platform}" if platform else ""
        prompt = (
            f"Перепиши следующий текст{platform_hint} в стиле «{style}».\n"
            f"Сохрани основной смысл, улучши структуру и читабельность.\n\n"
            f"Текст:\n{text}"
        )

        result = await cls._request([
            {"role": "system", "content": "Ты — редактор-копирайтер."},
            {"role": "user", "content": prompt},
        ])

        if user_id:
            await cls._log_request(user_id, "rewrite_text", prompt, result)

        return result

    @classmethod
    async def generate_comment(
        cls, post_text: str, tone: str = "позитивный", user_id: int | None = None,
    ) -> str:
        prompt = (
            f"Напиши комментарий к посту в {tone} тоне.\n"
            f"Комментарий должен быть естественным, 1-3 предложения.\n\n"
            f"Пост:\n{post_text}"
        )

        result = await cls._request([
            {"role": "system", "content": "Ты — активный подписчик канала."},
            {"role": "user", "content": prompt},
        ], max_tokens=256)

        if user_id:
            await cls._log_request(user_id, "generate_comment", prompt, result)

        return result

    @classmethod
    async def analyze_engagement(
        cls, posts_data: list[dict], user_id: int | None = None,
    ) -> str:
        posts_text = "\n\n".join(
            f"Пост {i+1} (лайки: {p.get('likes', 0)}, "
            f"репосты: {p.get('shares', 0)}, "
            f"комментарии: {p.get('comments', 0)}):\n{p.get('text', '')}"
            for i, p in enumerate(posts_data)
        )

        prompt = (
            f"Проанализируй вовлечённость по этим постам и дай рекомендации:\n\n"
            f"{posts_text}\n\n"
            f"Ответь в формате:\n"
            f"1. Общая оценка\n"
            f"2. Лучший пост и почему\n"
            f"3. Рекомендации по улучшению\n"
            f"4. Оптимальное время публикации\n"
        )

        result = await cls._request([
            {"role": "system", "content": "Ты — аналитик социальных сетей."},
            {"role": "user", "content": prompt},
        ], max_tokens=2048)

        if user_id:
            await cls._log_request(user_id, "analyze_engagement", prompt, result)

        return result

    @classmethod
    async def build_funnel_advice(
        cls, niche: str, goal: str, user_id: int | None = None,
    ) -> str:
        prompt = (
            f"Построй автоворонку продаж для ниши «{niche}» с целью «{goal}».\n\n"
            f"Распиши:\n"
            f"1. Этапы воронки (5-7 шагов)\n"
            f"2. Контент для каждого этапа\n"
            f"3. Триггеры перехода между этапами\n"
            f"4. Примеры сообщений\n"
            f"5. KPI для каждого этапа\n"
        )

        result = await cls._request([
            {"role": "system", "content": "Ты — эксперт по маркетинговым воронкам."},
            {"role": "user", "content": prompt},
        ], max_tokens=3000)

        if user_id:
            await cls._log_request(user_id, "build_funnel", prompt, result)

        return result

    @classmethod
    async def ab_rewrite(
        cls, text: str, user_id: int | None = None,
    ) -> tuple[str, str]:
        """Создать два варианта текста для A/B тестирования."""
        prompt = (
            f"Создай два РАЗНЫХ варианта поста на основе текста ниже.\n"
            f"Вариант A — более формальный и информативный.\n"
            f"Вариант B — более эмоциональный и провокационный.\n\n"
            f"Раздели варианты строкой «---SPLIT---».\n\n"
            f"Исходный текст:\n{text}"
        )

        result = await cls._request([
            {"role": "system", "content": "Ты — A/B тестировщик контента."},
            {"role": "user", "content": prompt},
        ], max_tokens=3000)

        parts = result.split("---SPLIT---")
        variant_a = parts[0].strip() if len(parts) > 0 else text
        variant_b = parts[1].strip() if len(parts) > 1 else text

        if user_id:
            await cls._log_request(user_id, "ab_rewrite", prompt, result)

        return variant_a, variant_b

    @classmethod
    async def _log_request(
        cls, user_id: int, request_type: str, prompt: str, response: str
    ) -> None:
        try:
            async with Database.session() as session:
                from app.db.models import AuditLog
                log = AuditLog(
                    user_id=user_id,
                    action=f"ai:{request_type}",
                    entity_type="ai_request",
                    details={
                        "prompt_length": len(prompt),
                        "response_length": len(response),
                    },
                )
                session.add(log)
        except Exception as e:
            logger.error(f"Failed to log AI request: {e}")