# app/api/server.py
from aiohttp import web
import orjson

from app.utils.security import validate_webapp_data, verify_api_token
from app.db.database import Database
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.post_repo import PostRepository
from app.db.repositories.task_repo import TaskRepository
from app.services.payments.yukassa import PaymentService
from app.services.cache.redis_cache import RedisCache
from app.services.integrations.crm_webhook import CRMWebhookService
from app.config import settings


def json_response(data: dict, status: int = 200) -> web.Response:
    return web.Response(
        body=orjson.dumps(data),
        content_type="application/json",
        status=status,
    )


async def webapp_auth(request: web.Request) -> int | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user_id = verify_api_token(token)
        if user_id:
            return user_id

    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if init_data:
        user_data = validate_webapp_data(init_data)
        if user_data:
            return user_data.get("id")

    return None


async def api_dashboard(request: web.Request) -> web.Response:
    user_id = await webapp_auth(request)
    if not user_id:
        return json_response({"error": "Unauthorized"}, 401)

    async with Database.session() as session:
        sub_repo = SubscriptionRepository(session)
        sub = await sub_repo.get_active(user_id)
        limits = await sub_repo.get_plan_limits(user_id)

        post_repo = PostRepository(session)
        posts = await post_repo.get_user_posts(user_id, limit=10)

        task_repo = TaskRepository(session)
        tasks = await task_repo.get_user_tasks(user_id, limit=10)

    return json_response({
        "subscription": {
            "plan": sub.plan if sub else "free",
            "status": sub.status if sub else "none",
            "expires_at": sub.expires_at.isoformat() if sub and sub.expires_at else None,
        },
        "limits": limits,
        "recent_posts": [
            {
                "id": str(p.id),
                "content": p.content[:100] if p.content else "",
                "status": p.status or "draft",
                "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
            }
            for p in posts
        ],
        "recent_tasks": [
            {
                "id": str(t.id),
                "title": t.title or "",
                "status": t.status or "pending",
                "type": t.task_type or "",
            }
            for t in tasks
        ],
    })


async def api_create_post(request: web.Request) -> web.Response:
    user_id = await webapp_auth(request)
    if not user_id:
        return json_response({"error": "Unauthorized"}, 401)

    data = await request.json()
    content = data.get("content", "")
    scheduled_at_str = data.get("scheduled_at")
    platforms = data.get("platforms", ["telegram"])

    if not content:
        return json_response({"error": "Content required"}, 400)

    from datetime import datetime
    schedule_dt = None
    if scheduled_at_str:
        schedule_dt = datetime.fromisoformat(scheduled_at_str)

    async with Database.session() as session:
        repo = PostRepository(session)
        post = await repo.create(
            user_id=user_id,
            content=content,
            scheduled_at=schedule_dt,
            platforms=platforms,
        )

    return json_response({
        "id": str(post.id),
        "status": post.status or "draft",
    }, 201)


async def api_analytics(request: web.Request) -> web.Response:
    user_id = await webapp_auth(request)
    if not user_id:
        return json_response({"error": "Unauthorized"}, 401)

    cached = await RedisCache.get(f"analytics:user:{user_id}")
    if cached:
        return json_response(cached)

    try:
        async with Database.session() as session:
            from sqlalchemy import func, select
            from app.db.models import Post, Task

            posts_count = (await session.execute(
                select(func.count(Post.id)).where(Post.user_id == user_id)
            )).scalar() or 0

            published = (await session.execute(
                select(func.count(Post.id)).where(
                    Post.user_id == user_id,
                    Post.status == "published",
                )
            )).scalar() or 0

            tasks_count = (await session.execute(
                select(func.count(Task.id)).where(Task.user_id == user_id)
            )).scalar() or 0

        analytics = {
            "total_posts": posts_count,
            "published_posts": published,
            "total_tasks": tasks_count,
        }

        await RedisCache.set(f"analytics:user:{user_id}", analytics, ttl=300)
        return json_response(analytics)
    except Exception:
        return json_response({"total_posts": 0, "published_posts": 0, "total_tasks": 0})


async def yukassa_webhook(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        success = await PaymentService.process_webhook(data)
        if success:
            return json_response({"status": "ok"})
        return json_response({"status": "error"}, 400)
    except Exception as e:
        return json_response({"status": "error", "message": str(e)}, 500)


async def crm_webhook(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        result = await CRMWebhookService.process_incoming_webhook(data)
        return json_response(result)
    except Exception as e:
        return json_response({"error": str(e)}, 500)
