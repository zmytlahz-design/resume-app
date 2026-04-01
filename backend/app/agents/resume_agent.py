"""Deterministic resume analysis agent with step-wise SSE output."""
import json
import asyncio
import time
from typing import AsyncGenerator
from app.tools.pdf_parser import run_pdf_parser
from app.tools.jd_matcher import run_jd_matcher
from app.tools.stack_checker import run_stack_checker
from app.tools.star_checker import run_star_checker
from app.tools.suggestion_gen import run_suggestion_generator_async


class ResumeAgent:
    """
    简历诊断 Agent（流程编排器）。

    设计定位：
    - 只负责“按顺序调度工具 + SSE 输出 + 异常降级”，不在这里做复杂业务计算。
    - 工具本身（pdf/jd/stack/star/suggestion）各司其职，Agent 负责把它们串成可观测流水线。
    - 每一步都产出可读事件（thinking/observation/report_chunk），前端可以实时展示进度。
    """

    # Keep a minimum gap between step events for UI readability.
    _MIN_STEP_GAP = 1.8

    def __init__(self):
        self.tool_results = {}
        self.report_text: str = ""   # 供 routes 在 run() 结束后读取，无需解析 SSE 字符串
        self._last_yield_time = 0

    async def _pace(self):
        """Ensure a small gap between non-token step events."""
        now = time.time()
        gap = self._MIN_STEP_GAP - (now - self._last_yield_time)
        if gap > 0:
            await asyncio.sleep(gap)
        self._last_yield_time = time.time()

    async def run(
        self,
        file_bytes: bytes,
        job_title: str,
        job_description: str,
    ) -> AsyncGenerator[str, None]:
        """
        Agent 主入口，返回异步生成器用于 SSE 流式输出。
        :param file_bytes: PDF文件字节
        :param job_title: 目标职位名称
        :param job_description: JD描述

        运行总览（固定 5 步）：
        1) PDF 解析 -> 结构化简历
        2) JD 匹配 -> 匹配度与 JD 结构分析
        3) 技术栈覆盖 -> 必须/加分技能覆盖与缺失
        4) STAR 检查 -> 经历描述完整性评分
        5) 建议生成 -> 流式输出最终报告

        关键策略：
        - 同步工具统一放到线程池执行（to_thread），防止阻塞事件循环。
        - 严格失败模式：关键步骤异常即停止并返回 error 事件。
        """

        _t0 = time.time()
        def _ts(): return f"[AGENT {time.time()-_t0:.3f}s]"
        self._last_yield_time = time.time()

        # ── Step 1: PDF 解析 ─────────────────────────────
        # 先发 thinking 事件，让前端立即有反馈，避免长时间空白等待。
        print(f"{_ts()} YIELD thinking_1 (pdf)", flush=True)
        yield self._format_thinking("📄 正在解析简历PDF，提取结构化信息...")
        yield ": flush\n\n"
        self._last_yield_time = time.time()

        try:
            # run_pdf_parser 是同步函数；放到线程执行，避免卡住 asyncio 主循环。
            resume_data = await asyncio.to_thread(run_pdf_parser, file_bytes)
            self.tool_results["pdf_parser"] = resume_data
            if "error" in resume_data:
                # 解析阶段若已明确不可恢复（如扫描件无法提取文本），直接结束流程。
                yield self._format_error(resume_data["error"])
                return
            await self._pace()
            print(f"{_ts()} YIELD observation_1 (pdf done)", flush=True)
            yield self._format_observation("tool_pdf_parser", f"成功提取简历，发现 {len(resume_data.get('work_experience', []))} 段工作经历，{len(resume_data.get('projects', []))} 个项目")
            yield ": flush\n\n"
            self._last_yield_time = time.time()
        except Exception as e:
            # 未预期异常：统一转为前端可读错误，避免连接中断。
            yield self._format_error(f"PDF解析失败：{str(e)}")
            return

        # ── Step 2: JD 匹配分析 ──────────────────────────
        await self._pace()
        print(f"{_ts()} YIELD thinking_2 (jd)", flush=True)
        yield self._format_thinking(f"🎯 正在分析简历与「{job_title}」职位的匹配度...")
        yield ": flush\n\n"
        self._last_yield_time = time.time()

        try:
            # 依赖 Step1 的 resume_data 作为输入。
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
            # 严格模式：JD 匹配失败即终止，不再降级继续。
            yield self._format_error(f"JD匹配失败：{str(e)}")
            return

        # ── Step 3: 技术栈覆盖率 ─────────────────────────
        await self._pace()
        print(f"{_ts()} YIELD thinking_3 (stack)", flush=True)
        yield self._format_thinking("🔧 正在检测技术栈覆盖率...")
        yield ": flush\n\n"
        self._last_yield_time = time.time()

        try:
            # Step3 基于 Step1（简历）+ Step2（JD结构）计算覆盖率。
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
            # 技术栈覆盖是核心指标，异常时直接报错终止，避免后续结论误导。
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
            yield self._format_error(f"STAR检查失败：{str(e)}")
            return

        # ── Step 5: 生成优化建议（流式）────────────────────
        await self._pace()
        print(f"{_ts()} YIELD thinking_5 (suggest)", flush=True)
        yield self._format_thinking("💡 所有分析完成，正在生成个性化优化建议...")
        yield ": flush\n\n"

        # 发送 report_start 分隔符，前端可据此切换到“报告渲染”模式。
        yield self._format_event("report_start", "")

        try:
            # 建议生成是 token 流式输出：边生成边推送，提升首字响应速度与交互体验。
            # 同时写入 self.report_text，让 routes 无需解析 SSE 字符串即可取到完整报告。
            async for delta in run_suggestion_generator_async(
                resume_data, job_title, jd_result, stack_result, star_result
            ):
                self.report_text += delta
                yield self._format_event("report_chunk", delta)
        except Exception as e:
            yield self._format_error(f"建议生成失败：{str(e)}")
            return

        yield self._format_event("report_end", "")
        # done 事件提供关键指标，便于前端做摘要展示或埋点统计。
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
        # SSE 规范要求每行都以 `data:` 前缀；多行文本需逐行前缀化。
        safe_data = str(data).encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        lines = safe_data.splitlines() or [""]
        payload = "\n".join(f"data: {line}" for line in lines)
        return f"event: {event_type}\n{payload}\n\n"
