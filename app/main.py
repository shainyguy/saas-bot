# app/main.py
import asyncio
import sys

# uvloop — опциональный, работаем и без него
try:
    import uvloop
    HAS_UVLOOP = True
except ImportError:
    HAS_UVLOOP = False

from aiohttp import web

from app.config import settings
from app.utils.logger import setup_logging, get_logger
from app.db.database import Database
from app.services.cache.redis_cache import RedisCache
from app.services.scheduler.jobs import setup_scheduler, scheduler
from app.bot.loader import bot, dp
from app.api.server import create_app

# Handlers
from app.bot.handlers import start, subscription, ai_handlers, automation, admin

# Middlewares
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.throttling import ThrottlingMiddleware
from app.bot.middlewares.subscription import SubscriptionMiddleware

setup_logging()
logger = get_logger(__name__)


async def on_startup(app: web.Application):
    """Инициализация при старте."""
    logger.info("Starting SaaS Bot...")

    # Database
    await Database.initialize()
    logger.info("Database connected")

    # Redis
    await RedisCache.initialize()
    logger.info("Redis connected")

    # Register middlewares
    dp.message.middleware(ThrottlingMiddleware(rate_limit=10, window=10))
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(SubscriptionMiddleware())

    # Register handlers
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(subscription.router)
    dp.include_router(ai_handlers.router)
    dp.include_router(automation.router)

    # Scheduler
    setup_scheduler()
    logger.info("Scheduler started")

    # Webhook
    if settings.BOT_WEBHOOK_URL:
        webhook_url = f"{settings.BOT_WEBHOOK_URL}{settings.BOT_WEBHOOK_PATH}"
        await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
        )
        logger.info(f"Webhook set: {webhook_url}")

        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
        webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_handler.register(app, path=settings.BOT_WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
    else:
        asyncio.create_task(dp.start_polling(bot, drop_pending_updates=True))
        logger.info("Polling started")

    logger.info("SaaS Bot fully started!")


async def on_shutdown(app: web.Application):
    """Очистка при остановке."""
    logger.info("Shutting down...")
    scheduler.shutdown(wait=False)

    if settings.BOT_WEBHOOK_URL:
        await bot.delete_webhook()

    await bot.session.close()
    await RedisCache.close()
    await Database.close()
    logger.info("Shutdown complete")


def main():
    # Установить uvloop только если доступен и не Windows
    if HAS_UVLOOP and sys.platform != "win32":
        uvloop.install()
        logger.info("uvloop installed as event loop policy")
    else:
        logger.info("Running with default asyncio event loop")

    # Создать aiohttp приложение
    app = create_app()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    logger.info(f"Starting server on {settings.APP_HOST}:{settings.APP_PORT}")
    web.run_app(
        app,
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        print=None,
    )


if __name__ == "__main__":
    main()
