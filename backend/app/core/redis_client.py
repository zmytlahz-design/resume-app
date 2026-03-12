"""
Redis 客户端封装

⭐ 面试考点：为什么用 Redis 代替内存字典？
   1. 进程重启不丢数据 —— 内存字典重启即清空，Redis 持久化不受影响
   2. 多进程/多容器共享会话 —— 水平扩展时多个 worker 都能读到同一份历史
   3. 自动 TTL 过期 —— 不需要手动清理过期 session，避免内存泄漏

用在哪：
   - session:{session_id}  →  对话历史列表（TTL 2h，用户长时间离开自动清理）
   - cache:{session_id}    →  简历解析结果（TTL 2h，追问时直接读取不重复解析）
"""
import json
import os

import redis

# ⭐ 面试考点：TTL 设 2h
#    - 太短：用户喝个咖啡回来 session 没了，体验差
#    - 太长：Redis 内存浪费，生产按业务需求权衡
SESSION_TTL = 60 * 60 * 2  # 2 小时

# decode_responses=True：让 Redis 返回 str 而不是 bytes，省去手动 decode
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),   # Docker 网络内服务名就是 "redis"
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
)


def session_set(session_id: str, messages: list[dict]) -> None:
    """写入完整会话历史，同时重置 TTL"""
    r.setex(
        f"session:{session_id}",
        SESSION_TTL,
        json.dumps(messages, ensure_ascii=False),
    )


def session_get(session_id: str) -> list[dict] | None:
    """读取会话历史；key 不存在时返回 None（用于判断 session 是否有效）"""
    data = r.get(f"session:{session_id}")
    return json.loads(data) if data else None


def session_append(session_id: str, message: dict) -> None:
    """追加一条消息并刷新 TTL（每次对话都顺延 2h 过期时间）"""
    messages = session_get(session_id) or []
    messages.append(message)
    session_set(session_id, messages)


def cache_set(session_id: str, data: dict) -> None:
    """缓存简历解析结果，TTL 与会话对齐"""
    r.setex(
        f"cache:{session_id}",
        SESSION_TTL,
        json.dumps(data, ensure_ascii=False),
    )


def cache_get(session_id: str) -> dict | None:
    """读取缓存的简历解析结果"""
    data = r.get(f"cache:{session_id}")
    return json.loads(data) if data else None
