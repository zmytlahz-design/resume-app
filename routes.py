"""
API 路由层
⭐ 面试考点：
   1. SSE (Server-Sent Events) vs WebSocket：
      - SSE：单向（服务端→客户端），HTTP协议，适合流式输出
      - WebSocket：双向实时，协议更复杂，适合聊天室
      我们用SSE因为只需要服务端推送流式文本
   
   2. Session 管理：
      - 用字典存对话历史（dict key = session_id）
      - 生产环境应该用 Redis，但两天项目内存够用
   
   3. 为什么 session_id 用 UUID？
      - 全局唯一，用户隔离，安全
"""
import uuid
import time
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.agents.resume_agent import ResumeAgent
# ⭐ 面试考点：用 Redis 代替内存字典
#    - 内存字典：进程重启即丢失，无法多副本共享
#    - Redis：持久化 + 自动 TTL + 容器间共享
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
    """SSE 安全编码：多行 data 需要逐行前缀 data:"""
    safe = _sanitize_text(data)
    lines = safe.splitlines() or [""]
    payload = "\n".join(f"data: {line}" for line in lines)
    return f"event: {event_type}\n{payload}\n\n"


def _compact_messages(
    messages: list[dict],
    max_chars: int = 12000,
    max_items: int = 12,
) -> list[dict]:
    """压缩上下文，避免历史过长导致供应商拒绝流式请求。"""
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
    
    前端用 fetch + ReadableStream 接收，或者用 EventSource
    ⭐ 注意：UploadFile + Form 混用时必须用 multipart/form-data
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
            "content": f"你是一位专业的简历顾问。用户正在应聘「{job_title}」职位。请根据简历分析结果回答用户的问题，给出具体、可操作的建议。"
        }
    ])

    agent = ResumeAgent()

    async def event_stream():
        """
        生成 SSE 事件流
        ⭐ 面试考点：为什么用 async generator？
           - 不阻塞，每生成一段数据立刻推送给前端
           - 用户不需要等全部完成才看到结果
        """
        t0 = time.time()
        # 先发送 session_id 给前端保存
        yield f"event: session_id\ndata: {session_id}\n\n"
        print(f"[SSE {time.time()-t0:.3f}s] session_id", flush=True)
        
        # 缓存简历内容供追问使用
        full_report = []
        
        async for chunk in agent.run(file_bytes, job_title, job_description):
            yield chunk
            # 调试日志：记录每条事件的交付时间
            tag = chunk[:50].replace('\n', '|')
            print(f"[SSE {time.time()-t0:.3f}s] {tag}", flush=True)
            # 提取报告内容加入对话历史
            if chunk.startswith("event: report_chunk"):
                content = chunk.split("data: ", 1)[-1].strip()
                full_report.append(content)
        
        # 把完整报告加入对话历史，供后续追问参考
        if full_report:
            session_append(session_id, {
                "role": "assistant",
                "content": "## 简历诊断报告\n" + "".join(full_report)
            })
        
        # 缓存简历解析结果
        cache_set(session_id, agent.tool_results)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲，确保实时推送
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
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    追问接口：基于已分析的简历继续对话
    ⭐ 面试考点：上下文管理
       - 把历史消息全部传给LLM，它就能"记住"之前的分析结果
       - 这就是会话式AI的本质：消息列表就是记忆
    """
    session_id = request.session_id
    
    if session_get(session_id) is None:
        raise HTTPException(status_code=404, detail="会话不存在，请先上传简历")

    user_message = _sanitize_text(request.message)

    from openai import AsyncOpenAI
    from app.core.config import get_settings
    settings = get_settings()

    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=90.0,
        max_retries=2,
    )

    # ⭐ 话题守卫：用 LLM 做意图分类
    #    把最近几条对话也给分类器看，这样"怎么改"在简历对话上下文中就不会被误判
    try:
        history = session_get(session_id) or []
        # 取最近 3 条历史（含 system prompt），让分类器知道这是简历会话
        recent = [
            {"role": m.get("role", "user"), "content": _sanitize_text(m.get("content", ""))[:200]}
            for m in history[-3:]
        ]
        guard_messages = [
            {
                "role": "system",
                "content": (
                    "你是一个意图分类器。当前对话场景是「AI简历诊断」。\n"
                    "判断用户最新消息结合上下文是否与「简历优化、求职、职位匹配、面试准备、职业规划、"
                    "改写经历描述」相关。\n"
                    "注意：用户可能用简短的话（如\"怎么改\"\"帮我改一下\"\"这个不好\"）来指代前面讨论的简历内容，"
                    "这种情况应判定为相关。\n"
                    "只与简历/求职完全无关的闲聊（如天气、笑话、写诗、股票）才判定为不相关。\n"
                    "只回答 YES 或 NO。"
                ),
            },
            *recent,
            {"role": "user", "content": user_message},
        ]
        guard_resp = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=guard_messages,
            temperature=0,
            max_tokens=5,
            stream=False,
        )
        guard_answer = (guard_resp.choices[0].message.content or "").strip().upper()
        topic_ok = guard_answer.startswith("Y")
    except Exception:
        topic_ok = True  # 分类器异常时放行，避免误伤

    if not topic_ok:
        async def _reject_stream():
            yield _sse_event("chat_chunk", "我只能回答与简历诊断和求职相关的问题，请重新提问 😊")
            yield _sse_event("chat_end", "done")
        return StreamingResponse(
            _reject_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    session_append(session_id, {"role": "user", "content": user_message})

    async def chat_stream():
        full_reply = []
        safe_messages = [
            {"role": m.get("role", "user"), "content": _sanitize_text(m.get("content", ""))}
            for m in (session_get(session_id) or [])
        ]

        async def _stream_once(stream_messages: list[dict]):
            # 智谱等兼容供应商不支持 .stream() 上下文管理器，
            # 必须用 .create(stream=True) 才能拿到真实 token 流。
            stream = await client.chat.completions.create(
                model=settings.deepseek_model,
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
        except UnicodeEncodeError:
            # 降级兜底：编码异常时也要给用户可读回复，避免前端报错。
            fallback_reply = (
                "抱歉，聊天服务遇到了编码兼容问题，我已切换到降级模式。\n\n"
                "你可以继续追问，我建议按下面方式提问会更稳定：\n"
                "1. 一次只问一个具体问题（例如：帮我改写这段项目经历）。\n"
                "2. 少用特殊符号和超长段落。\n"
                "3. 如果需要，我可以先给你一个可直接粘贴到简历里的改写模板。"
            )
            session_append(session_id, {
                "role": "assistant",
                "content": fallback_reply
            })
            yield _sse_event("chat_chunk", fallback_reply)
            yield _sse_event("chat_end", "done")
        except Exception as e:
            # 主流式失败后，继续用更短上下文多次重试，尽量避免直接报错。
            err_text = str(e).lower()
            print(f"[chat_stream] primary stream failed: {type(e).__name__}: {str(e)}")

            retry_plans = [(8000, 8), (5000, 6), (3000, 4)]
            stream_ok = False
            last_error_text = err_text

            for max_chars, max_items in retry_plans:
                try:
                    full_reply.clear()
                    retry_messages = _compact_messages(
                        safe_messages,
                        max_chars=max_chars,
                        max_items=max_items,
                    )
                    async for evt in _stream_once(retry_messages):
                        yield evt

                    session_append(session_id, {
                        "role": "assistant",
                        "content": "".join(full_reply)
                    })
                    yield _sse_event("chat_end", "done")
                    stream_ok = True
                    break
                except Exception as e_retry:
                    last_error_text = f"{last_error_text} | {str(e_retry).lower()}"
                    print(
                        "[chat_stream] retry stream failed: "
                        f"{type(e_retry).__name__}: {str(e_retry)}"
                    )

            if not stream_ok:
                # 关键：不能抛异常，否则前端会看到 ERR_INCOMPLETE_CHUNKED_ENCODING
                if "insufficient balance" in last_error_text or "402" in last_error_text:
                    fallback_reply = "当前 AI 服务余额不足，暂时无法进行流式对话，请更换可用 API Key 后重试。"
                elif "rate" in last_error_text or "429" in last_error_text:
                    fallback_reply = "当前请求频率较高，流式通道被限流。请等待 5-10 秒后重试。"
                elif "timeout" in last_error_text or "timed out" in last_error_text:
                    fallback_reply = "模型响应超时，我已保留会话上下文。请重发一次同样问题。"
                elif "context" in last_error_text or "token" in last_error_text or "length" in last_error_text:
                    fallback_reply = "当前会话上下文过长导致流式失败。我已自动压缩上下文，请再发一次同样的问题。"
                else:
                    fallback_reply = "流式通道本次请求失败。请重试一次；若连续失败，我可以切换到稳定的非流式回复模式。"
                session_append(session_id, {
                    "role": "assistant",
                    "content": fallback_reply
                })
                yield _sse_event("chat_chunk", fallback_reply)
                yield _sse_event("chat_end", "done")
    
    return StreamingResponse(
        chat_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health")
async def health_check():
    """健康检查接口，部署后用来验证服务是否正常"""
    return {"status": "ok", "message": "简历诊断Agent服务运行中-v4-friendly-fallback"}
