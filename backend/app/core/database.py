"""SQLAlchemy async engine, session factory, and ORM models."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from app.core.config import get_settings

SESSION_TTL_HOURS = 2


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _expires_utc() -> datetime:
    return _now_utc() + timedelta(hours=SESSION_TTL_HOURS)


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_title = Column(String(256), nullable=False, default="")
    job_description = Column(Text, nullable=False, default="")
    report_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    expires_at = Column(DateTime(timezone=True), nullable=False, default=_expires_utc)

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.id")
    tool_results = relationship("ToolResult", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False)
    content = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    session = relationship("Session", back_populates="messages")


class ToolResult(Base):
    __tablename__ = "tool_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_name = Column(String(128), nullable=False)
    result_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)

    session = relationship("Session", back_populates="tool_results")


def _make_engine():
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


_engine = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as db:
        yield db


async def create_all() -> None:
    """Create all tables (idempotent – safe to call on every startup)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
