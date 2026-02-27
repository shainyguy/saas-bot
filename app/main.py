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


async def health(request):
    return web.json_response({"status": "ok"})


async def on_startup(app):
    print("[STARTUP] Init...", flush=True)

    from app.config import settings

    if not settings.is_token_set:
        print("[STARTUP] BOT_TOKEN not set!", flush=True)
        return

    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    test_bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        me = await test_bot.get_me()
        print(f"[STARTUP] Bot @{me.username}", flush=True)
    except Exception as e:
        print(f"[STARTUP] Token invalid: {e}", flush=True)
        await test_bot.session.close()
        return
    finally:
        await test_bot.session.close()

    if settings.DATABASE_URL:
        try:
            from app.db.database import Database
            await Database.initialize()
            print("[STARTUP] Database OK", flush=True)
        except Exception as e:
            print(f"[STARTUP] Database error: {e}", flush=True)

    if settings.REDIS_URL:
        try:
            from app.services.cache.redis_cache import RedisCache
            await RedisCache.initialize()
            print(f"[STARTUP] Redis: {RedisCache.is_available()}", flush=True)
        except Exception as e:
            print(f"[STARTUP] Redis error: {e}", flush=True)

    try:
        from app.bot.loader import bot, dp
        from app.bot.middlewares.auth import AuthMiddleware
        from app.bot.middlewares.throttling import ThrottlingMiddleware
        from app.bot.middlewares.subscription import SubscriptionMiddleware
        from app.bot.handlers import start
        from app.bot.handlers import subscription
        from app.bot.handlers import ai_handlers
        from app.bot.handlers import automation
        from app.bot.handlers import admin

        dp.message.middleware(ThrottlingMiddleware(rate_limit=10, window=10))
        dp.message.middleware(AuthMiddleware())
        dp.callback_query.middleware(AuthMiddleware())
        dp.message.middleware(SubscriptionMiddleware())

        dp.include_router(admin.router)
        dp.include_router(start.router)
        dp.include_router(subscription.router)
        dp.include_router(ai_handlers.router)
        dp.include_router(automation.router)
        print("[STARTUP] Handlers OK", flush=True)
    except Exception as e:
        print(f"[STARTUP] Handlers error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return

    try:
        from app.services.scheduler.jobs import setup_scheduler
        setup_scheduler()
        print("[STARTUP] Scheduler OK", flush=True)
    except Exception as e:
        print(f"[STARTUP] Scheduler error: {e}", flush=True)

    if settings.BOT_WEBHOOK_URL:
        url = settings.BOT_WEBHOOK_URL + settings.BOT_WEBHOOK_PATH
        try:
            await bot.set_webhook(url=url, drop_pending_updates=True)
            from aiogram.webhook.aiohttp_server import SimpleRequestHandler
            from aiogram.webhook.aiohttp_server import setup_application
            handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
            handler.register(app, path=settings.BOT_WEBHOOK_PATH)
            setup_application(app, dp, bot=bot)
            print(f"[STARTUP] Webhook: {url}", flush=True)
        except Exception as e:
            print(f"[STARTUP] Webhook failed: {e}", flush=True)
            asyncio.create_task(dp.start_polling(bot, drop_pending_updates=True))
    else:
        asyncio.create_task(dp.start_polling(bot, drop_pending_updates=True))
        print("[STARTUP] Polling started", flush=True)

    print("[STARTUP] READY!", flush=True)


async def on_shutdown(app):
    print("[SHUTDOWN] Cleaning...", flush=True)
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
        from app.services.cache.redis_cache import RedisCache
        await RedisCache.close()
    except Exception:
        pass
    try:
        from app.db.database import Database
        await Database.close()
    except Exception:
        pass
    print("[SHUTDOWN] Done", flush=True)


def main():
    if HAS_UVLOOP and sys.platform != "win32":
        uvloop.install()

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    try:
        from app.api.server import api_dashboard
        from app.api.server import api_create_post
        from app.api.server import api_analytics
        from app.api.server import yukassa_webhook
        from app.api.server import crm_webhook

        app.router.add_get("/api/dashboard", api_dashboard)
        app.router.add_post("/api/posts", api_create_post)
        app.router.add_get("/api/analytics", api_analytics)
        app.router.add_post("/webhook/yukassa", yukassa_webhook)
        app.router.add_post("/webhook/crm", crm_webhook)
        print("[INIT] API routes loaded", flush=True)
    except Exception as e:
        print(f"[INIT] API routes skipped: {e}", flush=True)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    print(f"[INIT] Starting {HOST}:{PORT}", flush=True)
    web.run_app(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
