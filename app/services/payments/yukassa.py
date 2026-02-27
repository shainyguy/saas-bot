# app/services/payments/yukassa.py
from yookassa import Configuration, Payment as YKPayment
from yookassa.domain.response import PaymentResponse
from uuid import uuid4
from datetime import datetime, timezone

from app.config import settings, PlanType
from app.db.database import Database
from app.db.repositories.subscription_repo import SubscriptionRepository
from app.db.repositories.user_repo import UserRepository
from app.db.models import Payment, PaymentStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Инициализация ЮKassa SDK
Configuration.account_id = settings.YUKASSA_SHOP_ID
Configuration.secret_key = settings.YUKASSA_SECRET_KEY

PLAN_DURATION = {
    PlanType.STARTER: 30,
    PlanType.PRO: 30,
    PlanType.BUSINESS: 30,
    PlanType.WEEKLY: 7,
}


class PaymentService:

    @staticmethod
    async def create_payment(user_id: int, plan: PlanType) -> dict:
        """Создать платёж в ЮKassa и вернуть URL для оплаты."""
        amount = settings.PLAN_PRICES.get(plan)
        if not amount:
            raise ValueError(f"Unknown plan: {plan}")

        amount_rub = amount / 100  # копейки → рубли
        idempotency_key = str(uuid4())

        payment: PaymentResponse = YKPayment.create(
            {
                "amount": {
                    "value": f"{amount_rub:.2f}",
                    "currency": "RUB",
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"{settings.WEBAPP_URL}/payment/success",
                },
                "capture": True,
                "description": f"Подписка {plan.value} — SaaS Bot",
                "metadata": {
                    "user_id": str(user_id),
                    "plan": plan.value,
                },
                "receipt": {
                    "customer": {"email": "payment@bot.com"},
                    "items": [
                        {
                            "description": f"Подписка {plan.value}",
                            "quantity": "1.00",
                            "amount": {
                                "value": f"{amount_rub:.2f}",
                                "currency": "RUB",
                            },
                            "vat_code": 1,
                        }
                    ],
                },
            },
            idempotency_key,
        )

        # Сохранить в БД
        async with Database.session() as session:
            db_payment = Payment(
                user_id=user_id,
                yukassa_payment_id=payment.id,
                amount=amount_rub,
                plan=plan.value,
                status=PaymentStatus.PENDING,
                description=f"Подписка {plan.value}",
                metadata_={"idempotency_key": idempotency_key},
            )
            session.add(db_payment)

        logger.info(
            "Payment created",
            user_id=user_id,
            plan=plan.value,
            yukassa_id=payment.id,
        )

        return {
            "payment_id": payment.id,
            "confirmation_url": payment.confirmation.confirmation_url,
            "amount": amount_rub,
            "plan": plan.value,
        }

    @staticmethod
    async def process_webhook(event_data: dict) -> bool:
        """Обработать вебхук от ЮKassa."""
        event_type = event_data.get("event")
        payment_obj = event_data.get("object", {})
        yukassa_id = payment_obj.get("id")

        if event_type != "payment.succeeded":
            logger.info(f"Ignoring event: {event_type}")
            return True

        metadata = payment_obj.get("metadata", {})
        user_id = int(metadata.get("user_id", 0))
        plan_str = metadata.get("plan", "")

        if not user_id or not plan_str:
            logger.error(f"Invalid metadata in payment {yukassa_id}")
            return False

        try:
            plan = PlanType(plan_str)
        except ValueError:
            logger.error(f"Unknown plan in payment: {plan_str}")
            return False

        duration = PLAN_DURATION.get(plan, 30)

        async with Database.session() as session:
            # Обновить статус платежа
            from sqlalchemy import update
            from app.db.models import Payment as PaymentModel
            await session.execute(
                update(PaymentModel)
                .where(PaymentModel.yukassa_payment_id == yukassa_id)
                .values(
                    status=PaymentStatus.SUCCEEDED,
                    confirmed_at=datetime.now(timezone.utc),
                )
            )

            # Активировать подписку
            sub_repo = SubscriptionRepository(session)
            await sub_repo.activate(
                user_id=user_id,
                plan=plan,
                duration_days=duration,
                yukassa_id=yukassa_id,
            )

        logger.info(
            "Payment succeeded, subscription activated",
            user_id=user_id,
            plan=plan.value,
        )
        return True

    @staticmethod
    async def check_payment_status(yukassa_payment_id: str) -> dict:
        payment = YKPayment.find_one(yukassa_payment_id)
        return {
            "id": payment.id,
            "status": payment.status,
            "paid": payment.paid,
            "amount": payment.amount.value,
        }