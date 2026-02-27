# app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from enum import Enum
from typing import Optional
import os


class PlanType(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"
    WEEKLY = "weekly"


class PlanLimits:
    """Лимиты для каждого тарифного плана"""
    LIMITS = {
        PlanType.FREE: {
            "channels": 1,
            "tasks": 5,
            "ai_requests_daily": 10,
            "autopost_daily": 3,
            "crosspost": False,
            "triggers": 2,
            "google_sheets": False,
            "crm_integration": False,
            "ab_testing": False,
        },
        PlanType.STARTER: {
            "channels": 3,
            "tasks": 50,
            "ai_requests_daily": 100,
            "autopost_daily": 30,
            "crosspost": False,
            "triggers": 10,
            "google_sheets": True,
            "crm_integration": False,
            "ab_testing": False,
        },
        PlanType.PRO: {
            "channels": 10,
            "tasks": 500,
            "ai_requests_daily": 500,
            "autopost_daily": 100,
            "crosspost": True,
            "triggers": 50,
            "google_sheets": True,
            "crm_integration": True,
            "ab_testing": True,
        },
        PlanType.BUSINESS: {
            "channels": -1,  # unlimited
            "tasks": -1,
            "ai_requests_daily": -1,
            "autopost_daily": -1,
            "crosspost": True,
            "triggers": -1,
            "google_sheets": True,
            "crm_integration": True,
            "ab_testing": True,
        },
        PlanType.WEEKLY: {
            "channels": 5,
            "tasks": 100,
            "ai_requests_daily": 200,
            "autopost_daily": 50,
            "crosspost": True,
            "triggers": 20,
            "google_sheets": True,
            "crm_integration": False,
            "ab_testing": False,
        },
    }

    @classmethod
    def get(cls, plan: PlanType) -> dict:
        return cls.LIMITS.get(plan, cls.LIMITS[PlanType.FREE])


class Settings(BaseSettings):
    # === Telegram ===
    BOT_TOKEN: str
    ADMIN_IDS: list[int] = Field(default_factory=list)
    WEBAPP_URL: str = ""
    BOT_WEBHOOK_URL: str = ""
    BOT_WEBHOOK_PATH: str = "/webhook/bot"

    # === Database ===
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # === Redis ===
    REDIS_URL: str = "redis://localhost:6379/0"

    # === ЮKassa ===
    YUKASSA_SHOP_ID: str = ""
    YUKASSA_SECRET_KEY: str = ""
    YUKASSA_WEBHOOK_SECRET: str = ""

    # === AI ===
    GIGACHAT_API_KEY: str = ""
    GIGACHAT_SCOPE: str = "GIGACHAT_API_PERS"

    # === Integrations ===
    VK_ACCESS_TOKEN: str = ""
    INSTAGRAM_ACCESS_TOKEN: str = ""
    GOOGLE_CREDENTIALS_JSON: str = ""

    # === App ===
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # === Plans Pricing ===
    PLAN_PRICES: dict = {
        PlanType.STARTER: 49000,    # копейки → 490₽
        PlanType.PRO: 149000,       # 1490₽
        PlanType.BUSINESS: 399000,  # 3990₽
        PlanType.WEEKLY: 39000,     # 390₽
    }

    TRIAL_DAYS: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def admin_ids_set(self) -> set[int]:
        return set(self.ADMIN_IDS)


settings = Settings()