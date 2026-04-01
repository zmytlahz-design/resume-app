"""Tool 5: generate final resume optimization report.

该模块负责“最终文案生成”：
- 输入前序工具的结构化结果；
- 产出 markdown 报告（流式 token）。
"""
from openai import OpenAI, AsyncOpenAI
from typing import AsyncGenerator
from app.core.config import get_settings

settings = get_settings()
client = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)


def _sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")


def _build_prompt(
    resume_data: dict,
    job_title: str,
    jd_result: dict,
    stack_result: dict,
    star_result: dict,
) -> str:
    # Prompt 只做“信息整合与表达”，计算逻辑由前置工具完成。
    return f"""你是一位资深 HR 和技术面试官，请根据以下简历分析结果，为候选人生成专业的优化建议报告。

## 目标职位
{job_title}

## 分析结果汇总

### JD 匹配分析
- 整体匹配度：{jd_result.get('match_score')}%（{jd_result.get('match_level')}匹配）
- JD要求技能：{', '.join(jd_result.get('jd_analysis', {}).get('required_skills', []))}

### 技术栈覆盖情况
- 覆盖率：{stack_result.get('coverage_rate')}%
- 已覆盖必须技能：{', '.join(stack_result.get('covered_required', []))}
- 缺失必须技能：{', '.join(stack_result.get('missing_required', []))}
- 缺失加分项技能：{', '.join(stack_result.get('missing_preferred', []))}

### STAR法则检查
- 平均得分：{star_result.get('overall_star_score')}/10
- 最薄弱的经历：{[r['title'] for r in star_result.get('results', []) if r.get('star_score', 10) < 6]}

## 要求
请生成一份专业的诊断报告，包含以下结构（使用Markdown格式）：

1. **总体评估**（2-3句话，直接告知匹配程度和核心问题）
2. **优势亮点**（3条，告诉候选人哪里做得好）
3. **核心问题**（按优先级排列，最多5条）
4. **具体改写示例**（至少给1条经历的改写前后对比）
5. **行动建议**（本周就能做的3件事）

语气：专业但友好，直接指出问题，给出可操作的建议。"""


def run_suggestion_generator(
    resume_data: dict,
    job_title: str,
    jd_result: dict,
    stack_result: dict,
    star_result: dict,
) -> str:
    """
    Tool 5 同步流式入口。
    说明：当前 Agent 主流程主要走 async 版本，这里保留为可复用接口。
    汇总所有工具结果，生成结构化优化建议。
    :return: Markdown 格式的建议报告（用于流式输出）
    """
    prompt = _build_prompt(resume_data, job_title, jd_result, stack_result, star_result)

    prompt = _sanitize_text(prompt)

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,  # 开启流式输出
        temperature=0.7,  # 适度提高温度，让建议更自然
    )
    return response  # 返回流式响应对象


async def run_suggestion_generator_async(
    resume_data: dict,
    job_title: str,
    jd_result: dict,
    stack_result: dict,
    star_result: dict,
) -> AsyncGenerator[str, None]:
    """
    异步流式入口（Agent 实际调用路径）。

    返回值是逐段 token（delta）：
    - Agent 会把每个 delta 包装成 SSE `report_chunk` 发给前端；
    - 前端边收边渲染，用户可实时看到报告生成过程。
    """
    prompt = _build_prompt(resume_data, job_title, jd_result, stack_result, star_result)
    prompt = _sanitize_text(prompt)

    async_client = AsyncOpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
    )
    stream = await async_client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        temperature=0.7,
    )
    async for chunk in stream:
        # 兼容不同服务商的 chunk 结构：先判空再取 delta content。
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0].delta, "content", None)
        if delta:
            yield _sanitize_text(delta)
