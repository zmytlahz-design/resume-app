"""Deterministic resume analysis agent with step-wise SSE output."""
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
    简历诊断 Agent，使用固定工具链保证稳定性和可观测性。
    """

    # Keep a minimum gap between step events for UI readability.
    _MIN_STEP_GAP = 1.8

    def __init__(self):
        self.tool_results = {}
        self._last_yield_time = 0

    async def _pace(self):
        """Ensure a small gap between non-token step events."""
        now = time.time()
        gap = self._MIN_STEP_GAP - (now - self._last_yield_time)
        if gap > 0:
            await asyncio.sleep(gap)
        self._last_yield_time = time.time()

    async def _emit_report_text(self, text: str):
        """Forward incremental report text as SSE chunks."""
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
            # Stream report tokens asynchronously to avoid blocking the event loop.
            async for delta in run_suggestion_generator_async(
                resume_data, job_title, jd_result, stack_result, star_result
            ):
                yield self._format_event("report_chunk", delta)
        except Exception as e:
            # Fall back to a local markdown template if model generation fails.
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
        """Build SSE payload in `event + data + blank line` format."""
        # Prefix each data line to preserve multi-line payloads.
        safe_data = str(data).encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        lines = safe_data.splitlines() or [""]
        payload = "\n".join(f"data: {line}" for line in lines)
        return f"event: {event_type}\n{payload}\n\n"
