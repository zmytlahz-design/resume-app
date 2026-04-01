"""API routes for resume analysis and follow-up chat."""
import uuid
import time
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.agents.resume_agent import ResumeAgent
from app.core.redis_client import cache_set, session_append, session_get, session_set

router = APIRouter(prefix="/api", tags=["resume"])


class ChatRequest(BaseModel):
    session_id: str
    message: str
    job_title: str
    job_description: str


def _sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")


def _sse_event(event_type: str, data: str) -> str:
    """Build an SSE event payload with safe UTF-8 text."""
    safe = _sanitize_text(data)
    lines = safe.splitlines() or [""]
    payload = "\n".join(f"data: {line}" for line in lines)
    return f"event: {event_type}\n{payload}\n\n"


def _compact_messages(
    messages: list[dict],
    max_chars: int = 12000,
    max_items: int = 12,
) -> list[dict]:
    """Trim chat history to keep streaming requests within provider limits."""
    if not messages:
        return []

    system_msg = None
    rest: list[dict] = []
    for m in messages:
        role = m.get("role", "user")
        content = _sanitize_text(m.get("content", ""))
        item = {"role": role, "content": content}
        if role == "system" and system_msg is None:
            system_msg = item
        else:
            rest.append(item)

    selected_rev: list[dict] = []
    total = 0
    for m in reversed(rest):
        content = m["content"]
        remaining = max_chars - total
        if remaining <= 0:
            break
        if len(content) > remaining:
            content = content[-remaining:]
        selected_rev.append({"role": m["role"], "content": content})
        total += len(content)
        if len(selected_rev) >= max_items:
            break

    selected = list(reversed(selected_rev))
    if system_msg:
        return [system_msg, *selected]
    return selected


@router.post("/analyze")
async def analyze_resume(
    file: UploadFile = File(..., description="简历PDF文件"),
    job_title: str = Form(..., description="目标职位名称"),
    job_description: str = Form(..., description="职位描述JD"),
):
    """
    主接口：上传简历 + 职位信息，返回SSE流式诊断报告
    
    前端使用 fetch + ReadableStream 解析 SSE。
    """
    # 校验文件类型
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持PDF格式的简历")
    
    # 限制文件大小（10MB）
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过10MB")

    # 生成 session_id，用于后续追问
    session_id = str(uuid.uuid4())
    
    # 初始化对话历史（写入 Redis，TTL 2h）
    session_set(session_id, [
        {
            "role": "system",
            "content": "\n".join([
                f"你是一位专业的简历顾问，用户正在应聘「{job_title}」职位。",
                "你的职责范围：简历优化、经历描述改写、职位匹配分析、求职技巧、面试准备、职业规划。",
                "规则：",
                "1. 只回答与简历、求职、职业发展相关的问题，给出具体、可操作的建议。",
                "2. 如果用户问的与以上范围完全无关（如推荐电影、写诗、天气、股票等），礼貌拒绝并引导回到简历话题，回复控制在一句话内。",
                "3. 用户用简短的话（如\"怎么改\"\"这段不好\"）指代前面讨论的简历内容时，视为相关问题正常回答。",
            ])
        }
    ])

    agent = ResumeAgent()

    async def event_stream():
        """
        生成 SSE 事件流。
        router 只负责：发 session_id、透传 agent 产出的 SSE 块、run 结束后做持久化。
        事件类型（thinking/observation/report_chunk 等）的定义与格式化全部在 agent 内部。
        """
        t0 = time.time()
        # 先发送 session_id 给前端保存
        yield f"event: session_id\ndata: {session_id}\n\n"
        print(f"[SSE {time.time()-t0:.3f}s] session_id", flush=True)

        async for chunk in agent.run(file_bytes, job_title, job_description):
            yield chunk
            tag = chunk[:50].replace('\n', '|').encode('ascii', errors='replace').decode('ascii')
            print(f"[SSE {time.time()-t0:.3f}s] {tag}", flush=True)

        # run() 结束后直接从 agent 属性取报告文本，无需解析 SSE 字符串
        if agent.report_text:
            session_append(session_id, {
                "role": "assistant",
                "content": "## 简历诊断报告\n" + agent.report_text,
            })

        # 缓存工具链运行结果
        cache_set(session_id, agent.tool_results)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
        },
    )


@router.get("/test-stream")
async def test_stream():
    """调试用：测试 SSE 流式传输是否通畅（绕过 Agent 逻辑）"""
    import asyncio
    async def gen():
        t0 = time.time()
        for i in range(6):
            msg = f"event: thinking\ndata: 第{i+1}步 - 时间 {time.time()-t0:.3f}s\n\n"
            print(f"[test-stream {time.time()-t0:.3f}s] step {i+1}", flush=True)
            yield msg
            await asyncio.sleep(1.0)
    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    追问接口：基于已分析的简历继续对话。
    """
    session_id = request.session_id
    
    if session_get(session_id) is None:
        raise HTTPException(status_code=404, detail="会话不存在，请先上传简历")

    user_message = _sanitize_text(request.message)

    from openai import AsyncOpenAI
    from app.core.config import get_settings
    settings = get_settings()

    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=90.0,
        max_retries=2,
    )

    session_append(session_id, {"role": "user", "content": user_message})

    async def chat_stream():
        full_reply = []
        safe_messages = [
            {"role": m.get("role", "user"), "content": _sanitize_text(m.get("content", ""))}
            for m in (session_get(session_id) or [])
        ]

        async def _stream_once(stream_messages: list[dict]):
            # Some OpenAI-compatible providers require .create(stream=True).
            stream = await client.chat.completions.create(
                model=settings.llm_model,
                messages=stream_messages,
                temperature=0.7,
                stream=True,
            )
            emitted = 0
            async for chunk in stream:
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                delta_obj = getattr(choices[0], "delta", None)
                delta = getattr(delta_obj, "content", None)
                if not delta:
                    continue
                delta = _sanitize_text(delta)
                full_reply.append(delta)
                emitted += 1
                yield _sse_event("chat_chunk", delta)

            if emitted == 0:
                raise RuntimeError("empty_stream_response")

        try:
            primary_messages = _compact_messages(safe_messages, max_chars=12000, max_items=12)
            async for evt in _stream_once(primary_messages):
                yield evt

            # 把AI回复加入历史，保持上下文
            session_append(session_id, {
                "role": "assistant",
                "content": "".join(full_reply)
            })
            yield _sse_event("chat_end", "done")
        except Exception as e:
            # 严格失败模式：不做重试与降级提示，直接返回失败并结束。
            yield _sse_event("chat_chunk", f"聊天失败：{str(e)}")
            yield _sse_event("chat_end", "done")
    
    return StreamingResponse(
        chat_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/health")
async def health_check():
    """健康检查接口，部署后用来验证服务是否正常"""
    return {"status": "ok", "message": "简历诊断Agent服务运行中-v5-strict-fail"}
