"""
Tool 5: 优化建议生成器
⭐ 面试考点：
   这个 Tool 是 Agent 的最后一步，汇总所有工具的结果
   生成有针对性的优化建议，而不是泛泛而谈
   
   关键设计：把前4个工具的输出作为上下文传入 prompt
   这就是"工具编排"的价值 —— 每个工具专注一件事，最后汇总
"""
from openai import OpenAI, AsyncOpenAI
from typing import AsyncGenerator
from app.core.config import get_settings

settings = get_settings()
client = OpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
)


def _sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")


def _safe_join(items: list) -> str:
    return ", ".join(_sanitize_text(str(i)) for i in items if i is not None)


def build_fallback_report_markdown(
    job_title: str,
    jd_result: dict,
    stack_result: dict,
    star_result: dict,
) -> str:
    """模型生成失败时的本地模板报告，保证前端可展示结果。"""
    match_score = jd_result.get("match_score", 0)
    coverage_rate = stack_result.get("coverage_rate", 0)
    star_score = star_result.get("overall_star_score", 0)
    missing_required = stack_result.get("missing_required", [])

    level = "较高" if match_score >= 70 else "中等" if match_score >= 40 else "较低"
    missing_text = _safe_join(missing_required) if missing_required else "暂无"

    return f"""## 总体评估
目标岗位：{_sanitize_text(job_title)}。当前简历与岗位匹配度为 **{match_score}%**（{level}），技术栈覆盖率为 **{coverage_rate}%**，STAR 表达得分为 **{star_score}/10**。

## 优势亮点
- 具备与目标岗位相关的基础能力，并已形成可展示的项目经历。
- 简历结构化信息完整，可继续优化关键词命中率。
- 已完成初步诊断，可快速进入定向修改阶段。

## 核心问题
- 必须技能缺失：{missing_text}
- 项目描述存在“结果量化不足”风险，建议补充指标（如性能提升、转化率、效率提升）。
- 职责描述偏泛化，建议改成“动作+技术+结果”表达。

## 具体改写示例
改写前：负责前端页面开发与接口联调。

改写后：基于 Vue3 + TypeScript 重构核心业务页面，封装 12 个复用组件；完成与 FastAPI 接口联调并优化请求缓存策略，使页面首屏加载时间下降约 28%。

## 行动建议
1. 本周优先补齐 2-3 个缺失必须技能，并在项目中体现。
2. 每段经历至少补 1 条可量化结果（百分比、时长、成本、成功率）。
3. 按目标岗位 JD 关键词重排技能与项目顺序，提高 ATS 命中率。
"""


def _build_prompt(
    resume_data: dict,
    job_title: str,
    jd_result: dict,
    stack_result: dict,
    star_result: dict,
) -> str:
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
    Tool 5 对外统一入口
    汇总所有工具结果，生成结构化优化建议
    :return: Markdown 格式的建议报告（用于流式输出）
    """
    prompt = _build_prompt(resume_data, job_title, jd_result, stack_result, star_result)

    # 注意：这里返回的是 generator，供流式输出使用
    prompt = _sanitize_text(prompt)

    response = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,  # 开启流式输出
        temperature=0.7,  # 稍高温度，建议更有创意
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
    ⭐ 面试考点：为什么用 AsyncOpenAI 而不是 OpenAI？
       同步 for chunk in stream 会阻塞事件循环，导致其他 SSE 事件无法 flush
       AsyncOpenAI + async for 让每个 token 到来时立即 yield，不阻塞
    """
    prompt = _build_prompt(resume_data, job_title, jd_result, stack_result, star_result)
    prompt = _sanitize_text(prompt)

    async_client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )
    stream = await async_client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
        temperature=0.7,
    )
    async for chunk in stream:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0].delta, "content", None)
        if delta:
            yield _sanitize_text(delta)
