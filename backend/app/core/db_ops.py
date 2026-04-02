"""PostgreSQL-backed session/cache helpers.

Drop-in async replacement for redis_client.py.
All public functions keep the same names; callers must await them.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Message, Session, ToolResult, get_session_factory

SESSION_TTL_HOURS = 2


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _expires_utc() -> datetime:
    return _now_utc() + timedelta(hours=SESSION_TTL_HOURS)


def _factory() -> AsyncSession:
    """Return a new async session context-manager from the shared factory."""
    return get_session_factory()()


# ---------------------------------------------------------------------------
# Session helpers (mirror redis_client.session_*)
# ---------------------------------------------------------------------------

async def session_init(session_id: str, job_title: str, job_description: str) -> None:
    """Create (or update) the session row with job metadata."""
    sid = uuid.UUID(session_id)
    async with _factory() as db:
        session_row = await db.get(Session, sid)
        if session_row is None:
            db.add(Session(
                id=sid,
                job_title=job_title,
                job_description=job_description,
                expires_at=_expires_utc(),
            ))
        else:
            session_row.job_title = job_title
            session_row.job_description = job_description
            session_row.expires_at = _expires_utc()
        await db.commit()


async def session_set(session_id: str, messages: list[dict]) -> None:
    """Replace the full message history for *session_id*.

    If the session row does not yet exist it is created automatically.
    """
    sid = uuid.UUID(session_id)
    async with _factory() as db:
        # Upsert session row
        result = await db.get(Session, sid)
        if result is None:
            result = Session(
                id=sid,
                expires_at=_expires_utc(),
            )
            db.add(result)
            await db.flush()
        else:
            result.expires_at = _expires_utc()

        # Delete existing messages and re-insert
        await db.execute(delete(Message).where(Message.session_id == sid))
        for m in messages:
            db.add(Message(
                session_id=sid,
                role=m.get("role", "user"),
                content=m.get("content", ""),
            ))

        await db.commit()


async def session_get(session_id: str) -> list[dict] | None:
    """Return the message list for *session_id*, or *None* if missing/expired."""
    sid = uuid.UUID(session_id)
    async with _factory() as db:
        session_row = await db.get(Session, sid)
        if session_row is None:
            return None
        if session_row.expires_at.replace(tzinfo=timezone.utc) < _now_utc():
            return None

        result = await db.execute(
            select(Message)
            .where(Message.session_id == sid)
            .order_by(Message.id)
        )
        rows = result.scalars().all()
        return [{"role": r.role, "content": r.content} for r in rows]


async def session_append(session_id: str, message: dict[str, Any]) -> None:
    """Append one message and refresh the session expiry."""
    sid = uuid.UUID(session_id)
    async with _factory() as db:
        session_row = await db.get(Session, sid)
        if session_row is None:
            # Create a minimal session row on demand
            session_row = Session(id=sid, expires_at=_expires_utc())
            db.add(session_row)
            await db.flush()
        else:
            session_row.expires_at = _expires_utc()

        db.add(Message(
            session_id=sid,
            role=message.get("role", "user"),
            content=message.get("content", ""),
        ))
        await db.commit()


# ---------------------------------------------------------------------------
# Cache helpers (mirror redis_client.cache_*)
# ---------------------------------------------------------------------------

async def cache_set(session_id: str, data: dict) -> None:
    """Persist tool results for *session_id*.

    Each key in *data* is stored as a separate ToolResult row.
    Existing rows for the session are replaced.
    """
    sid = uuid.UUID(session_id)
    async with _factory() as db:
        # Ensure session row exists
        session_row = await db.get(Session, sid)
        if session_row is None:
            session_row = Session(id=sid, expires_at=_expires_utc())
            db.add(session_row)
            await db.flush()

        # Replace tool results
        await db.execute(delete(ToolResult).where(ToolResult.session_id == sid))
        for tool_name, result in data.items():
            db.add(ToolResult(
                session_id=sid,
                tool_name=str(tool_name),
                result_json=json.dumps(result, ensure_ascii=False),
            ))

        await db.commit()


async def cache_get(session_id: str) -> dict | None:
    """Return cached tool results for *session_id*, or *None* if absent."""
    sid = uuid.UUID(session_id)
    async with _factory() as db:
        result = await db.execute(
            select(ToolResult).where(ToolResult.session_id == sid)
        )
        rows = result.scalars().all()
        if not rows:
            return None
        return {r.tool_name: json.loads(r.result_json) for r in rows}


# ---------------------------------------------------------------------------
# Report helper
# ---------------------------------------------------------------------------

async def report_set(session_id: str, report_text: str) -> None:
    """Persist the final report text on the session row."""
    sid = uuid.UUID(session_id)
    async with _factory() as db:
        session_row = await db.get(Session, sid)
        if session_row is not None:
            session_row.report_text = report_text
            await db.commit()


async def session_get_full(session_id: str) -> dict | None:
    """Return a dict with messages, tool_results, and report_text.

    Used by GET /api/sessions/{session_id} to restore frontend state.
    Returns None if the session is missing or expired.
    """
    sid = uuid.UUID(session_id)
    async with _factory() as db:
        session_row = await db.get(Session, sid)
        if session_row is None:
            return None
        if session_row.expires_at.replace(tzinfo=timezone.utc) < _now_utc():
            return None

        msgs_result = await db.execute(
            select(Message).where(Message.session_id == sid).order_by(Message.id)
        )
        messages = [
            {"role": r.role, "content": r.content}
            for r in msgs_result.scalars().all()
        ]

        tools_result = await db.execute(
            select(ToolResult).where(ToolResult.session_id == sid)
        )
        tool_results = {
            r.tool_name: json.loads(r.result_json)
            for r in tools_result.scalars().all()
        }

        return {
            "messages": messages,
            "tool_results": tool_results,
            "report_text": session_row.report_text or "",
        }


async def session_delete(session_id: str) -> bool:
    """Delete the session and all related rows.  Returns True if a row was deleted."""
    sid = uuid.UUID(session_id)
    async with _factory() as db:
        result = await db.execute(delete(Session).where(Session.id == sid))
        await db.commit()
        return result.rowcount > 0
