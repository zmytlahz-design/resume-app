"""
ReAct Agent 核心实现
⭐ 这是整个项目最重要的文件，面试必讲！

ReAct = Reasoning + Acting
原理：LLM 像人一样，先思考(Thought)，再行动(Action)，再观察结果(Observation)，循环直到完成任务

我们的 Agent 执行流程：
Thought: 我需要先解析简历PDF
Action: tool_call(pdf_parser)
Observation: {结构化简历数据}
Thought: 我需要分析与JD的匹配度
Action: tool_call(jd_matcher)
Observation: {匹配结果}
... 依此类推直到生成最终建议

⭐ 为什么这比直接调用LLM更好？
   1. 每个工具都是可测试、可调试的独立模块
   2. Agent可以根据中间结果动态决定下一步
   3. 这就是生产级AI应用的标准架构
"""
import json
import asyncio
import time
from typing import AsyncGenerator
from app.tools.pdf_parser import run_pdf_parser
from app.tools.jd_matcher import run_jd_matcher
from app.tools.stack_checker import run_stack_checker
from app.tools.star_checker import run_star_checker
from app.tools.suggestion_gen import run_suggestion_generator, run_suggestion_generator_async, build_fallback_report_markdown


class ResumeAgent:
    """
    简历诊断 Agent
    采用固定工具链模式（相比完全自主的ReAct，更稳定，适合生产）
    ⭐ 面试解释：这是 Deterministic Agent，工具调用顺序固定
       优点：稳定可预测，易于调试
       vs 完全自主Agent：LLM自决定调用哪些工具，创意更强但不稳定
    """

    # 前端打字机单步最长约 1.5s，需要保证后端两次 yield 之间至少有这么长间隔
    _MIN_STEP_GAP = 1.8

    def __init__(self):
        self.tool_results = {}
        self._last_yield_time = 0

    async def _pace(self):
        """保证与上一次 yield 之间有足够间隔，让前端打字机打完当前步骤"""
        now = time.time()
        gap = self._MIN_STEP_GAP - (now - self._last_yield_time)
        if gap > 0:
            await asyncio.sleep(gap)
        self._last_yield_time = time.time()

    async def _emit_report_text(self, text: str):
        """真流式：收到上游增量后立即透传给前端。"""
        piece = str(text or "")
        if piece:
            yield self._format_event("report_chunk", piece)

    async def run(
        self,
        file_bytes: bytes,
        job_title: str,
        job_description: str,
    ) -> AsyncGenerator[str, None]:
        """
        Agent 主入口，返回异步生成器用于 SSE 流式输出
        :param file_bytes: PDF文件字节
        :param job_title: 目标职位名称
        :param job_description: JD描述
        """

        _t0 = time.time()
        def _ts(): return f"[AGENT {time.time()-_t0:.3f}s]"
        self._last_yield_time = time.time()

        # ── Step 1: PDF 解析 ─────────────────────────────
        print(f"{_ts()} YIELD thinking_1 (pdf)", flush=True)
        yield self._format_thinking("📄 正在解析简历PDF，提取结构化信息...")
        yield ": flush\n\n"
        self._last_yield_time = time.time()

        try:
            resume_data = await asyncio.to_thread(run_pdf_parser, file_bytes)
            self.tool_results["pdf_parser"] = resume_data
            if "error" in resume_data:
                yield self._format_error(resume_data["error"])
                return
            await self._pace()
            print(f"{_ts()} YIELD observation_1 (pdf done)", flush=True)
            yield self._format_observation("tool_pdf_parser", f"成功提取简历，发现 {len(resume_data.get('work_experience', []))} 段工作经历，{len(resume_data.get('projects', []))} 个项目")
            yield ": flush\n\n"
            self._last_yield_time = time.time()
        except Exception as e:
            yield self._format_error(f"PDF解析失败：{str(e)}")
            return

        # ── Step 2: JD 匹配分析 ──────────────────────────
        await self._pace()
        print(f"{_ts()} YIELD thinking_2 (jd)", flush=True)
        yield self._format_thinking(f"🎯 正在分析简历与「{job_title}」职位的匹配度...")
        yield ": flush\n\n"
        self._last_yield_time = time.time()

        try:
            jd_result = await asyncio.to_thread(
                run_jd_matcher, resume_data, job_title, job_description
            )
            self.tool_results["jd_matcher"] = jd_result
            await self._pace()
            print(f"{_ts()} YIELD observation_2 (jd done)", flush=True)
            yield self._format_observation(
                "tool_jd_matcher",
                f"匹配度：{jd_result['match_score']}%（{jd_result['match_level']}匹配）"
            )
            yield ": flush\n\n"
            self._last_yield_time = time.time()
        except Exception as e:
            jd_result = {
                "match_score": 0.0,
                "jd_analysis": {
                    "required_skills": [],
                    "preferred_skills": [],
                    "responsibilities": [],
                    "years_of_experience": 0,
                    "education_requirement": "",
                },
                "match_level": "低",
                "warning": f"jd_matcher_exception: {type(e).__name__}",
            }
            self.tool_results["jd_matcher"] = jd_result
            yield self._format_observation("tool_jd_matcher", "JD匹配异常，已切换兜底模式继续分析")
            self._last_yield_time = time.time()

        # ── Step 3: 技术栈覆盖率 ─────────────────────────
        await self._pace()
        print(f"{_ts()} YIELD thinking_3 (stack)", flush=True)
        yield self._format_thinking("🔧 正在检测技术栈覆盖率...")
        yield ": flush\n\n"
        self._last_yield_time = time.time()

        try:
            stack_result = await asyncio.to_thread(
                run_stack_checker, resume_data, jd_result["jd_analysis"]
            )
            self.tool_results["stack_checker"] = stack_result
            await self._pace()
            print(f"{_ts()} YIELD observation_3 (stack done)", flush=True)
            yield self._format_observation(
                "tool_stack_checker",
                stack_result["summary"]
            )
            yield ": flush\n\n"
            self._last_yield_time = time.time()
        except Exception as e:
            yield self._format_error(f"技术栈检测失败：{str(e)}")
            return

        # ── Step 4: STAR 法则检查 ─────────────────────────
        await self._pace()
        print(f"{_ts()} YIELD thinking_4 (star)", flush=True)
        yield self._format_thinking("⭐ 正在检查经历描述的STAR法则完整性...")
        yield ": flush\n\n"
        self._last_yield_time = time.time()

        try:
            star_result = await asyncio.to_thread(run_star_checker, resume_data)
            self.tool_results["star_checker"] = star_result
            await self._pace()
            print(f"{_ts()} YIELD observation_4 (star done)", flush=True)
            yield self._format_observation(
                "tool_star_checker",
                star_result.get("summary", "STAR检查完成")
            )
            yield ": flush\n\n"
            self._last_yield_time = time.time()
        except Exception as e:
            star_result = {"overall_star_score": 0, "results": [], "summary": "检查跳过"}
            yield self._format_observation("tool_star_checker", "STAR检查跳过（经历描述为空）")
            self._last_yield_time = time.time()

        # ── Step 5: 生成优化建议（流式）────────────────────
        await self._pace()
        print(f"{_ts()} YIELD thinking_5 (suggest)", flush=True)
        yield self._format_thinking("💡 所有分析完成，正在生成个性化优化建议...")
        yield ": flush\n\n"

        # 发送分隔符，前端识别后切换到报告渲染模式
        yield self._format_event("report_start", "")

        try:
            # ⭐ 面试考点：用 AsyncOpenAI + async for，不阻塞事件循环
            #    原来的同步 for chunk in stream 会卡住 event loop，导致
            #    前面 yield 的 thinking/observation 事件全部积压到最后才 flush
            async for delta in run_suggestion_generator_async(
                resume_data, job_title, jd_result, stack_result, star_result
            ):
                yield self._format_event("report_chunk", delta)
        except Exception as e:
            # 生成失败时回退到本地模板报告，避免流程中断。
            fallback_report = build_fallback_report_markdown(
                job_title=job_title,
                jd_result=jd_result,
                stack_result=stack_result,
                star_result=star_result,
            )
            reason = "模型服务暂时不可用"
            err_text = str(e).lower()
            if "insufficient balance" in err_text or "402" in err_text:
                reason = "模型服务余额不足"
            yield self._format_observation("tool_suggestion_gen", f"建议生成异常（{reason}），已启用模板报告")
            async for piece in self._emit_report_text(fallback_report):
                yield piece

        yield self._format_event("report_end", "")
        yield self._format_event("done", json.dumps({
            "match_score": jd_result.get("match_score"),
            "coverage_rate": stack_result.get("coverage_rate"),
            "star_score": star_result.get("overall_star_score"),
        }))

    def _format_thinking(self, thought: str) -> str:
        """格式化 Thought 步骤的 SSE 消息"""
        return self._format_event("thinking", thought)

    def _format_observation(self, tool_name: str, result: str) -> str:
        """格式化 Observation 步骤的 SSE 消息"""
        return self._format_event("observation", json.dumps({
            "tool": tool_name,
            "result": result
        }))

    def _format_error(self, message: str) -> str:
        return self._format_event("error", message)

    @staticmethod
    def _format_event(event_type: str, data: str) -> str:
        """
        SSE (Server-Sent Events) 标准格式
        格式：event: 类型\ndata: 数据\n\n
        前端用 EventSource 接收
        """
        # SSE 规范：多行数据需要每行都加 data: 前缀，否则前端会解析丢失。
        safe_data = str(data).encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        lines = safe_data.splitlines() or [""]
        payload = "\n".join(f"data: {line}" for line in lines)
        return f"event: {event_type}\n{payload}\n\n"
