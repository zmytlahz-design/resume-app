"""
Tool 2: JD 职位描述匹配器
⭐ 面试考点（这是最重要的工具！）：
   - 用 embedding 把文本变成向量，再算余弦相似度
   - 这就是 RAG 的核心思路：文本 → 向量 → 相似度检索
   - 为什么不用 pgvector？原理一样，两天内先跑通，后期无缝替换
"""
import numpy as np
import re
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


def _fallback_extract_jd_keywords(job_title: str, job_description: str) -> dict:
    """
    LLM 调用失败时的本地兜底提取。
    仅提取基础字段，保证后续流程继续。
    """
    text = f"{job_title}\n{job_description}".lower()
    known_skills = [
        "python", "java", "javascript", "typescript", "vue", "react", "node",
        "fastapi", "django", "flask", "mysql", "postgresql", "redis", "docker",
        "kubernetes", "git", "linux", "pandas", "numpy", "sql", "html", "css",
    ]
    required = [s for s in known_skills if s in text]

    # 粗略识别年限
    years = 0
    m = re.search(r"(\d+)\s*年", text)
    if m:
        years = int(m.group(1))

    return {
        "required_skills": required,
        "preferred_skills": [],
        "responsibilities": [],
        "years_of_experience": years,
        "education_requirement": "",
    }


def get_embedding(text: str) -> list[float]:
    """
    调用配置中的 embedding 接口（如智谱 embedding-3），把文本转为向量
    ⭐ 这就是 RAG 第一步：Embedding
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
    ⭐ 面试必问：为什么用余弦相似度而不是欧氏距离？
       因为我们关心方向（语义）而不是大小（长度），
       长短文本都能公平比较
    """
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def extract_jd_keywords(job_title: str, job_description: str) -> dict:
    """
    用 LLM 从 JD 中提取关键要求
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

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        import json
        return json.loads(response.choices[0].message.content)
    except UnicodeEncodeError:
        return _fallback_extract_jd_keywords(job_title, job_description)
    except Exception:
        return _fallback_extract_jd_keywords(job_title, job_description)


def run_jd_matcher(resume_data: dict, job_title: str, job_description: str) -> dict:
    """
    Tool 2 对外统一入口
    计算简历与JD的匹配程度
    """
    try:
        job_title = _sanitize_text(job_title)
        job_description = _sanitize_text(job_description)

        # 1. 提取JD关键词
        jd_keywords = extract_jd_keywords(job_title, job_description)

        # 2. 用向量相似度计算整体匹配度
        # 把简历技能和工作经历拼成文本
        resume_skills = [str(s) for s in resume_data.get('skills', [])]
        resume_text = f"""
        技能：{', '.join(resume_skills)}
        经历：{' '.join([
            exp.get('position', '') + ' ' + ' '.join(exp.get('responsibilities', []))
            for exp in resume_data.get('work_experience', [])
        ])}
        """
        resume_text = _sanitize_text(resume_text)

        try:
            # 尝试用向量相似度（需要 embedding API 支持）
            resume_vec = get_embedding(resume_text[:2000])  # 限制长度
            jd_vec = get_embedding(job_description[:2000])
            similarity_score = cosine_similarity(resume_vec, jd_vec)
            match_percent = round(similarity_score * 100, 1)
        except Exception:
            # 如果 embedding 接口不可用，用关键词匹配兜底
            resume_skills_lower = [s.lower() for s in resume_skills]
            required = jd_keywords.get('required_skills', [])
            matched = sum(1 for skill in required if any(skill.lower() in rs for rs in resume_skills_lower))
            match_percent = round((matched / max(len(required), 1)) * 100, 1)

        return {
            "match_score": match_percent,
            "jd_analysis": jd_keywords,
            "match_level": "高" if match_percent >= 70 else "中" if match_percent >= 40 else "低",
        }
    except Exception as e:
        # 兜底：任何异常都返回可继续的默认结构，避免中断整个Agent流程。
        fallback_jd = _fallback_extract_jd_keywords(_sanitize_text(job_title), _sanitize_text(job_description))
        return {
            "match_score": 0.0,
            "jd_analysis": fallback_jd,
            "match_level": "低",
            "warning": f"jd_matcher_fallback: {type(e).__name__}",
        }
