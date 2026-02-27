# app/db/database.py
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.config import settings


class Base(DeclarativeBase):
    pass


class Database:
    _engine: AsyncEngine | None = None
    _session_factory: async_sessionmaker[AsyncSession] | None = None

    @classmethod
    async def initialize(cls) -> None:
        cls._engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.DEBUG,
        )
        cls._session_factory = async_sessionmaker(
            bind=cls._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        print("[DB] Engine created", flush=True)

    @classmethod
    async def close(cls) -> None:
        if cls._engine:
            await cls._engine.dispose()

    @classmethod
    @asynccontextmanager
    async def session(cls) -> AsyncGenerator[AsyncSession, None]:
        if not cls._session_factory:
            raise RuntimeError("Database not initialized")
        async with cls._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @classmethod
    def get_session_factory(cls) -> async_sessionmaker[AsyncSession]:
        if not cls._session_factory:
            raise RuntimeError("Database not initialized")
        return cls._session_factory
