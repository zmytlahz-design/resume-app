"""Redis-backed session/cache helpers."""
import json
from functools import lru_cache
from typing import Any

from redis import Redis
from app.core.config import get_settings

SESSION_TTL = 60 * 60 * 2  # 2 小时
SESSION_PREFIX = "resume:session:"
CACHE_PREFIX = "resume:cache:"


def _session_key(session_id: str) -> str:
    return f"{SESSION_PREFIX}{session_id}"


def _cache_key(session_id: str) -> str:
    return f"{CACHE_PREFIX}{session_id}"


@lru_cache(maxsize=1)
def _redis_client() -> Redis:
    settings = get_settings()
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password or None,
        decode_responses=True,
    )


def session_set(session_id: str, messages: list[dict]) -> None:
    """写入完整会话历史，同时重置 TTL。"""
    payload = json.dumps(list(messages), ensure_ascii=False)
    _redis_client().setex(_session_key(session_id), SESSION_TTL, payload)


def session_get(session_id: str) -> list[dict] | None:
    """读取会话历史；会话不存在或已过期时返回 None。"""
    payload = _redis_client().get(_session_key(session_id))
    if payload is None:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, list) else None


def session_append(session_id: str, message: dict[str, Any]) -> None:
    """追加一条消息并刷新 TTL（每次对话都顺延 2h 过期时间）。"""
    messages = session_get(session_id) or []
    messages.append(dict(message))
    session_set(session_id, messages)


def cache_set(session_id: str, data: dict) -> None:
    """缓存简历解析结果，TTL 与会话对齐。"""
    payload = json.dumps(dict(data), ensure_ascii=False)
    _redis_client().setex(_cache_key(session_id), SESSION_TTL, payload)


def cache_get(session_id: str) -> dict | None:
    """读取缓存的简历解析结果；不存在或过期返回 None。"""
    payload = _redis_client().get(_cache_key(session_id))
    if payload is None:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
