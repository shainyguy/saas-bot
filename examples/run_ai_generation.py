# examples/run_ai_generation.py
"""Пример AI-генерации через GigaChat."""
import asyncio
from app.services.ai.gigachat import GigaChatService
from app.db.database import Database
from app.services.cache.redis_cache import RedisCache


async def example_ai():
    await Database.initialize()
    await RedisCache.initialize()

    # 1. Генерация поста
    post = await GigaChatService.generate_post(
        topic="Тренды AI в 2025 году",
        style="экспертный",
        platform="telegram",
        user_id=123456789,
    )
    print("=== GENERATED POST ===")
    print(post)

    # 2. Рерайт под VK
    vk_version = await GigaChatService.rewrite_text(
        text=post,
        style="неформальный",
        platform="vk",
        user_id=123456789,
    )
    print("\n=== VK VERSION ===")
    print(vk_version)

    # 3. A/B тест
    variant_a, variant_b = await GigaChatService.ab_rewrite(
        text=post,
        user_id=123456789,
    )
    print("\n=== A/B TEST ===")
    print(f"A: {variant_a[:200]}...")
    print(f"B: {variant_b[:200]}...")

    # 4. Воронка
    funnel = await GigaChatService.build_funnel_advice(
        niche="онлайн-курсы",
        goal="продажа курса по Python",
        user_id=123456789,
    )
    print("\n=== FUNNEL ===")
    print(funnel[:500])

    await RedisCache.close()
    await Database.close()


if __name__ == "__main__":
    asyncio.run(example_ai())