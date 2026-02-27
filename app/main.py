# app/main.py
import asyncio
import os
import sys

print("=" * 50, flush=True)
print("SAAS BOT STARTING", flush=True)
print(f"Python {sys.version}", flush=True)
print(f"PORT={os.environ.get('PORT', 'not set')}", flush=True)
print("=" * 50, flush=True)

try:
    import uvloop
    HAS_UVLOOP = True
except ImportError:
    HAS_UVLOOP = False

from aiohttp import web

PORT = int(os.environ.get("PORT", 8080))
HOST = "0.0.0.0"


# === Health — всегда работает ===
async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


# === Startup ===
async def on_startup(app: web.Application):
    print("[STARTUP] Init...", flush=True)

    from app.config import settings

    # 1. Проверить токен
    if not settings.is_token_set:
        print("[STARTUP] ❌ BOT_TOKEN not set!", flush=True)
        return

    # 2. Проверить токен у Telegram
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    test_bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        me = await test_bot.get_me()
        print(f"[STARTUP] ✅ Bot @{me.username}", flush=True)
    except Exception as e:
        print(f"[STARTUP] ❌ Token invalid: {e}", flush=True)
        await test_bot.session.close()
        return
    finally:
        await test_bot.session.close()

    # 3. Database
    if settings.DATABASE_URL:
        try:
            print(f"[STARTUP] DB URL prefix: {settings.DATABASE_URL[:30]}...", flush=True)
            from app.db.database import Database
            await Database.initialize()
            print("[STARTUP] ✅ Database OK", flush=True)
        except Exception as e:
            print(f"[STARTUP] ❌ Database: {e}", flush=True)
    else:
        print("[STARTUP] ⚠️ No DATABASE_URL", flush=True)

    # 4. Redis
    if settings.REDIS_URL:
        try:
            from app.services.cache.redis_cache import RedisCache
            await RedisCache.initialize()
            s = "OK" if RedisCache.is_available() else "unavailable"
            print(f"[STARTUP] {'✅' if RedisCache.is_available() else '⚠️'} Redis: {s}", flush=True)
        except Exception as e:
            print(f"[STARTUP] ⚠️ Redis: {e}", flush=True)
    else:
        print("[STARTUP] ⚠️ No REDIS_URL", flush=True)

    # 5. Bot handlers
    try:
        from app.bot.loader import bot, dp
        from app.bot.middlewares.auth import AuthMiddleware
        from app.bot.middlewares.throttling import ThrottlingMiddleware
        from app.bot.middlewares.subscription import SubscriptionMiddleware
        from app.bot.handlers import start, subscription, ai_handlers, automation, admin

        dp.message.middleware(ThrottlingMiddleware(rate_limit=10, window=10))
        dp.message.middleware(AuthMiddleware())
        dp.callback_query.middleware(AuthMiddleware())
        dp.message.middleware(SubscriptionMiddleware())

        dp.include_router(admin.router)
        dp.include_router(start.router)
        dp.include_router(subscription.router)
        dp.include_router(ai_handlers.router)
        dp.include_router(automation.router)
        print("[STARTUP] ✅ Handlers OK", flush=True)
    except Exception as e:
        print(f"[STARTUP] ❌ Handlers: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return

    # 6. Scheduler
    try:
        from app.services.scheduler.jobs import setup_scheduler
        setup_scheduler()
        print("[STARTUP] ✅ Scheduler OK", flush=True)
    except Exception as e:
        print(f"[STARTUP] ⚠️ Scheduler: {e}", flush=True)

    # 7. Webhook or Polling
    if settings.BOT_WEBHOOK_URL:
        url = f"{settings.BOT_WEBHOOK_URL}{settings.BOT_WEBHOOK_PATH}"
        try:
            await bot.set_webhook(url=url, drop_pending_updates=True)
            from aiogram.webhook.aiohttp_server import (
                SimpleRequestHandler, setup_application
            )
            h = SimpleRequestHandler(dispatcher=dp, bot=bot)
            h.register(app, path=settings.BOT_WEBHOOK_PATH)
            setup_application(app, dp, bot=bot)
            print(f"[STARTUP] ✅ Webhook: {url}", flush=True)
        except Exception as e:
            print(f"[STARTUP] ⚠️ Webhook failed: {e}, using polling", flush=True)
            asyncio.create_task(dp.start_polling(bot, drop_pending_updates=True))
    else:
        asyncio.create_task(dp.start_polling(bot, drop_pending_updates=True))
        print("[STARTUP] ✅ Polling started", flush=True)

    print("[STARTUP] 🚀 READY!", flush=True)


async def on_shutdown(app: web.Application):
    print("[SHUTDOWN] ...", flush=True)
    try:
        from app.services.scheduler.jobs import scheduler
        scheduler.shutdown(wait=False)
    except Exception:
        pass
    try:
        from app.bot.loader import bot
        await bot.session.close()
    except Exception:
        pass
    try:
        from 
