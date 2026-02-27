# app/bot/loader.py
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)


def create_dispatcher() -> Dispatcher:
    """Создать Dispatcher с доступным storage."""
    storage = MemoryStorage()

    # Попробовать Redis storage, fallback на Memory
    if settings.REDIS_URL:
        try:
            from aiogram.fsm.storage.redis import RedisStorage
            storage = RedisStorage.from_url(settings.REDIS_URL)
            logger.info("Using Redis FSM storage")
        except Exception as e:
            logger.warning(f"Redis FSM storage failed: {e}, using MemoryStorage")
            storage = MemoryStorage()
    else:
        logger.info("Using Memory FSM storage (no REDIS_URL)")

    return Dispatcher(storage=storage)


dp = create_dispatcher()
