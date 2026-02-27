# app/config.py
import os
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from enum import Enum


class PlanType(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"
    WEEKLY = "weekly"


class PlanLimits:
    LIMITS = {
        PlanType.FREE: {
            "channels": 1, "tasks": 5, "ai_requests_daily": 10,
            "autopost_daily": 3, "crosspost": False, "triggers": 2,
            "google_sheets": False, "crm_integration": False, "ab_testing": False,
        },
        PlanType.STARTER: {
            "channels": 3, "tasks": 50, "ai_requests_daily": 100,
            "autopost_daily": 30, "crosspost": False, "triggers": 10,
            "google_sheets": True, "crm_integration": False, "ab_testing": False,
        },
        PlanType.PRO: {
            "channels": 10, "tasks": 500, "ai_requests_daily": 500,
            "autopost_daily": 100, "crosspost": True, "triggers": 50,
            "google_sheets": True, "crm_integration": True, "ab_testing": True,
        },
        PlanType.BUSINESS: {
            "channels": -1, "tasks": -1, "ai_requests_daily": -1,
            "autopost_daily": -1, "crosspost": True, "triggers": -1,
            "google_sheets": True, "crm_integration": True, "ab_testing": True,
        },
        PlanType.WEEKLY: {
            "channels": 5, "tasks": 100, "ai_requests_daily": 200,
            "autopost_daily": 50, "crosspost": True, "triggers": 20,
            "google_sheets": True, "crm_integration": False, "ab_testing": False,
        },
    }

    @classmethod
    def get(cls, plan: "PlanType") -> dict:
        return cls.LIMITS.get(plan, cls.LIMITS[PlanType.FREE])


class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    ADMIN_IDS: list[int] = Field(default_factory=list)
    WEBAPP_URL: str = ""
    BOT_WEBHOOK_URL: str = ""
    BOT_WEBHOOK_PATH: str = "/webhook/bot"

    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    REDIS_URL: str = ""

    YUKASSA_SHOP_ID: str = ""
    YUKASSA_SECRET_KEY: str = ""

    GIGACHAT_API_KEY: str = ""
    GIGACHAT_SCOPE: str = "GIGACHAT_API_PERS"

    VK_ACCESS_TOKEN: str = ""
    INSTAGRAM_ACCESS_TOKEN: str = ""
    GOOGLE_CREDENTIALS_JSON: str = ""

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = int(os.environ.get("PORT", 8080))
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    PLAN_PRICES: dict = {
        PlanType.STARTER: 49000,
        PlanType.PRO: 149000,
        PlanType.BUSINESS: 399000,
        PlanType.WEEKLY: 39000,
    }

    TRIAL_DAYS: int = 3

    @field_validator("DATABASE_URL")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """Railway даёт postgresql://, нам нужен postgresql+asyncpg://"""
        if not v:
            return v
        # postgres:// → postgresql://
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        # postgresql:// → postgresql+asyncpg://
        elif v.startswith("postgresql://") and "+asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("BOT_TOKEN")
    @classmethod
    def validate_token_format(cls, v: str) -> str:
        if v and v != "123456:ABC-DEF":
            parts = v.split(":")
            if len(parts) != 2 or not parts[0].isdigit():
                raise ValueError("BOT_TOKEN wrong format. Get from @BotFather")
        return v

    @property
    def admin_ids_set(self) -> set[int]:
        return set(self.ADMIN_IDS)

    @property
    def is_token_set(self) -> bool:
        return bool(self.BOT_TOKEN) and self.BOT_TOKEN != "123456:ABC-DEF"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
