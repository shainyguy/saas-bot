# app/db/models.py
from sqlalchemy import (
    Column, BigInteger, String, Boolean, DateTime, Text,
    ForeignKey, Numeric, Integer, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid as uuid_lib
import enum

from app.db.database import Base


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PostStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    language_code = Column(String(10), default="ru")
    role = Column(String(20), default="user")
    is_blocked = Column(Boolean, default=False)
    referral_code = Column(String(32), unique=True)
    referred_by = Column(BigInteger)
    ai_requests_today = Column(Integer, default=0)
    ai_requests_reset_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    subscriptions = relationship("Subscription", back_populates="user", lazy="selectin")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    plan = Column(String(20), default="free")
    status = Column(String(20), default="trial")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    trial_ends_at = Column(DateTime(timezone=True))
    auto_renew = Column(Boolean, default=True)
    yukassa_subscription_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="subscriptions")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"))
    yukassa_payment_id = Column(String(255), unique=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB")
    status = Column(String(20), default="pending")
    plan = Column(String(20), nullable=False)
    description = Column(Text)
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime(timezone=True))


class Channel(Base):
    __tablename__ = "channels"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    telegram_channel_id = Column(BigInteger)
    title = Column(String(255))
    username = Column(String(255))
    is_active = Column(Boolean, default=True)
    vk_group_id = Column(String(255))
    instagram_account_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    channel_id = Column(BigInteger, ForeignKey("channels.id", ondelete="SET NULL"))
    content = Column(Text, nullable=False)
    media_urls = Column(JSONB, default=[])
    status = Column(String(20), default="draft")
    scheduled_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))
    platforms = Column(JSONB, default=["telegram"])
    ab_variant = Column(String(1))
    ab_group_id = Column(UUID(as_uuid=True))
    engagement_data = Column(JSONB, default={})
    metadata_ = Column("metadata", JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    task_type = Column(String(100), nullable=False)
    status = Column(String(20), default="pending")
    cron_expression = Column(String(100))
    is_recurring = Column(Boolean, default=False)
    payload = Column(JSONB, default={})
    result = Column(JSONB)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_run_at = Column(DateTime(timezone=True))
    last_run_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AutomationTrigger(Base):
    __tablename__ = "automation_triggers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    trigger_type = Column(String(50), nullable=False)
    trigger_config = Column(JSONB, default={})
    action_type = Column(String(50), nullable=False)
    action_config = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    executions_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Funnel(Base):
    __tablename__ = "funnels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    steps = Column(JSONB, default=[])
    is_active = Column(Boolean, default=False)
    subscribers_count = Column(Integer, default=0)
    conversion_rate = Column(Numeric(5, 2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    action = Column(String(255), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(String(255))
    details = Column(JSONB, default={})
    ip_address = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
