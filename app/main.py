# app/main.py
import asyncio
import sys

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
    try:
        await Database.initialize()
        logger.info("✅ Database connected")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise  # БД обязательна

    # Redis — опционально
    try:
        await RedisCache.initialize()
        if RedisCache.is_available():
            logger.info("✅ Redis connected")
        else:
            logger.warning("⚠️ Redis unavailable — running without cache")
    except Exception as e:
        logger.warning(f"⚠️ Redis init error: {e} — running without cache")

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
    try:
        setup_scheduler()
        logger.info("✅ Scheduler started")
    except Exception as e:
        logger.warning(f"⚠️ Scheduler failed: {e}")

    # Webhook
    if settings.BOT_WEBHOOK_URL:
        webhook_url = f"{settings.BOT_WEBHOOK_URL}{settings.BOT_WEBHOOK_PATH}"
        await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
        )
        logger.info(f"✅ Webhook set: {webhook_url}")

        from aiogram.webhook.aiohttp_server import (
            SimpleRequestHandler,
            setup_application,
        )
        webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_handler.register(app, path=settings.BOT_WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
    else:
        asyncio.create_task(dp.start_polling(bot, drop_pending_updates=True))
        logger.info("✅ Polling started")

    logger.info("🚀 SaaS Bot fully started!")


async def on_shutdown(app: web.Application):
    """Очистка при остановке."""
    logger.info("Shutting down...")

    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass

    if settings.BOT_WEBHOOK_URL:
        try:
            await bot.delete_webhook()
        except Exception:
            pass

    try:
        await bot.session.close()
    except Exception:
        pass

    await RedisCache.close()
    await Database.close()
    logger.info("👋 Shutdown complete")


def main():
    if HAS_UVLOOP and sys.platform != "win32":
        uvloop.install()
        logger.info("uvloop installed")
    else:
        logger.info("Using default asyncio event loop")

    app = create_app()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    logger.info(f"Starting on {settings.APP_HOST}:{settings.APP_PORT}")
    web.run_app(
        app,
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        print=None,
    )


if __name__ == "__main__":
    main()
