# app/services/automation/triggers.py
from sqlalchemy import select
from app.db.database import Database
from app.db.models import AutomationTrigger
from app.utils.logger import get_logger
from datetime import datetime, timezone

logger = get_logger(__name__)


class TriggerEngine:
    """Движок триггерной автоматизации: если X → сделать Y."""

    @staticmethod
    async def evaluate_trigger(
        trigger_type: str,
        context: dict,
        user_id: int | None = None,
    ) -> list[dict]:
        """Найти и выполнить все подходящие триггеры."""
        results = []

        async with Database.session() as session:
            stmt = select(AutomationTrigger).where(
                AutomationTrigger.is_active == True,
                AutomationTrigger.trigger_type == trigger_type,
            )
            if user_id:
                stmt = stmt.where(AutomationTrigger.user_id == user_id)

            result = await session.execute(stmt)
            triggers = result.scalars().all()

            for trigger in triggers:
                if TriggerEngine._match_condition(trigger.trigger_config, context):
                    action_result = await TriggerEngine._execute_action(
                        trigger.action_type, trigger.action_config, context
                    )
                    trigger.executions_count += 1
                    trigger.last_executed_at = datetime.now(timezone.utc)
                    results.append({
                        "trigger_id": str(trigger.id),
                        "action": trigger.action_type,
                        "result": action_result,
                    })
                    logger.info(
                        f"Trigger executed: {trigger.name}",
                        trigger_id=str(trigger.id),
                    )

        return results

    @staticmethod
    def _match_condition(config: dict, context: dict) -> bool:
        """Проверить условие триггера."""
        condition_type = config.get("condition", "always")

        if condition_type == "always":
            return True
        elif condition_type == "keyword_match":
            keywords = config.get("keywords", [])
            text = context.get("text", "").lower()
            return any(kw.lower() in text for kw in keywords)
        elif condition_type == "user_count_gt":
            return context.get("user_count", 0) > config.get("threshold", 0)

        return False

    @staticmethod
    async def _execute_action(
        action_type: str, action_config: dict, context: dict
    ) -> dict:
        """Выполнить действие триггера."""
        if action_type == "send_message":
            # Отправить сообщение через бот
            from app.bot.loader import bot
            chat_id = action_config.get("chat_id") or context.get("chat_id")
            text = action_config.get("text", "Автоматическое сообщение")
            if chat_id:
                await bot.send_message(chat_id=chat_id, text=text)
                return {"sent": True, "chat_id": chat_id}

        elif action_type == "call_webhook":
            import httpx
            url = action_config.get("url")
            if url:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json=context)
                    return {"status": resp.status_code}

        elif action_type == "add_to_sheet":
            from app.services.integrations.google_sheets import GoogleSheetsService
            spreadsheet_id = action_config.get("spreadsheet_id")
            sheet = action_config.get("sheet_name", "Sheet1")
            values = action_config.get("values_template", [])
            # Подставить значения из context
            row = [context.get(v, v) for v in values]
            await GoogleSheetsService.append_row(spreadsheet_id, sheet, row)
            return {"appended": True}

        elif action_type == "notify_admin":
            from app.bot.loader import bot
            from app.config import settings
            for admin_id in settings.ADMIN_IDS:
                text = action_config.get("text", f"Триггер сработал: {context}")
                await bot.send_message(chat_id=admin_id, text=str(text)[:4096])
            return {"notified": True}

        return {"action": action_type, "status": "unknown"}