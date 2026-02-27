# app/services/integrations/crm_webhook.py
import httpx
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CRMWebhookService:
    """Отправка данных во внешние CRM через вебхуки."""

    @staticmethod
    async def send_lead(
        webhook_url: str,
        lead_data: dict,
        headers: dict | None = None,
    ) -> bool:
        default_headers = {"Content-Type": "application/json"}
        if headers:
            default_headers.update(headers)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    webhook_url,
                    json=lead_data,
                    headers=default_headers,
                )
                response.raise_for_status()
                logger.info(f"Lead sent to CRM: {response.status_code}")
                return True
        except Exception as e:
            logger.error(f"CRM webhook failed: {e}")
            return False

    @staticmethod
    async def process_incoming_webhook(data: dict) -> dict:
        """Обработать входящий вебхук от CRM."""
        action = data.get("action")
        payload = data.get("payload", {})

        logger.info(f"Incoming CRM webhook: action={action}")

        if action == "new_lead":
            # Создать задачу на обработку
            from app.services.cache.redis_cache import RedisCache
            await RedisCache.enqueue_task("crm_leads", {
                "action": action,
                "payload": payload,
            })

        return {"status": "accepted", "action": action}