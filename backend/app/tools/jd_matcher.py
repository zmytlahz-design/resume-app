"""Tool 2: compute JD match score from resume data.

流程：
1) 从 JD 提取结构化关键词（LLM）；
2) 计算简历与 JD 的匹配分（embedding 余弦相似度）；
3) 输出统一结构供 Agent 与后续工具消费。
"""
import numpy as np
from openai import OpenAI
from app.core.config import get_settings

settings = get_settings()

client = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)


def _sanitize_text(text: str) -> str:
    """清洗潜在坏字符，减少底层编码异常概率。"""
    if not isinstance(text, str):
        text = str(text)
    return text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")


def get_embedding(text: str) -> list[float]:
    """
    调用 embedding 接口，将文本转换为向量。
    注意：该步骤依赖提供方支持 embedding 模型。
    """
    response = client.embeddings.create(
        model=settings.llm_embedding_model,
        input=text,
    )
    return response.data[0].embedding


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    余弦相似度 = 两向量夹角的余弦值
    值域 [-1, 1]，越接近1表示越相似
    通过余弦相似度衡量语义接近程度。
    """
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def extract_jd_keywords(job_title: str, job_description: str) -> dict:
    """
    用 LLM 从 JD 中提取关键要求。
    输出字段会被后续 stack_checker 直接使用，因此结构必须稳定。
    """
    job_title = _sanitize_text(job_title)
    job_description = _sanitize_text(job_description)

    prompt = f"""分析以下职位描述，提取关键信息，以JSON返回：
- required_skills: 必须的技术技能列表
- preferred_skills: 加分的技术技能列表  
- responsibilities: 核心职责列表（3-5条）
- years_of_experience: 要求工作年限（数字，没有则为0）
- education_requirement: 学历要求

职位名称：{job_title}
职位描述：{job_description}

只返回JSON。"""

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    import json
    return json.loads(response.choices[0].message.content)


def run_jd_matcher(resume_data: dict, job_title: str, job_description: str) -> dict:
    """
    Tool 2 对外统一入口：计算简历与 JD 的匹配程度。

    返回结构约定（严格模式）：
    {
      "match_score": float,
      "jd_analysis": {...},
      "match_level": "高/中/低",
    }

    说明：
    - 本函数不做降级兜底；任一步失败会抛异常，由上层直接返回失败。
    """
    job_title = _sanitize_text(job_title)
    job_description = _sanitize_text(job_description)

    # 1. 提取JD关键词
    jd_keywords = extract_jd_keywords(job_title, job_description)

    # 2. 计算整体匹配度：embedding 余弦相似度
    resume_skills = [str(s) for s in resume_data.get('skills', [])]
    resume_text = f"""
    技能：{', '.join(resume_skills)}
    经历：{' '.join([
        exp.get('position', '') + ' ' + ' '.join(exp.get('responsibilities', []))
        for exp in resume_data.get('work_experience', [])
    ])}
    """
    resume_text = _sanitize_text(resume_text)

    resume_vec = get_embedding(resume_text[:2000])  # 限制长度
    jd_vec = get_embedding(job_description[:2000])
    similarity_score = cosine_similarity(resume_vec, jd_vec)
    match_percent = round(similarity_score * 100, 1)

    return {
        "match_score": match_percent,
        "jd_analysis": jd_keywords,
        "match_level": "高" if match_percent >= 70 else "中" if match_percent >= 40 else "低",
    }
