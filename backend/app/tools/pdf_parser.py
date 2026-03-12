"""
Tool 1: PDF 简历解析器
⭐ 面试考点：
   - 为什么用 pdfplumber？支持表格提取，中文不乱码
   - 结构化提取：把非结构化PDF → 结构化字典，方便后续工具使用
   - 用 LLM 做结构化提取，比正则表达式更健壮
"""
import pdfplumber
import io
import re
from openai import OpenAI
from app.core.config import get_settings

settings = get_settings()

# DeepSeek 兼容 OpenAI SDK，只需改 base_url
client = OpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    从 PDF 字节流提取原始文本
    :param file_bytes: 上传文件的字节内容
    :return: 提取的纯文本
    """
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # 提取普通文本
            text = page.extract_text()
            if text:
                text_parts.append(text)
            # 提取表格（技能表、经历表常见）
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    row_text = " | ".join(cell or "" for cell in row)
                    text_parts.append(row_text)
    return "\n".join(text_parts)


def parse_resume_structure(raw_text: str) -> dict:
    """
    用 LLM 把原始文本 → 结构化简历数据
    ⭐ 这里是关键：prompt engineering 的实战应用
    :param raw_text: PDF提取的原始文本
    :return: 结构化简历字典
    """
    prompt = f"""请从以下简历文本中提取结构化信息，以JSON格式返回，包含以下字段：
- name: 姓名
- education: 教育经历列表（学校、专业、学历、时间）
- work_experience: 工作/实习经历列表（公司、职位、时间、职责描述列表）
- projects: 项目经历列表（项目名、技术栈、描述、成果）
- skills: 技能列表（编程语言、框架、工具等）
- summary: 个人简介（如有）

只返回JSON，不要其他解释。

简历文本：
{raw_text}
"""

    response = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},  # 强制JSON输出，避免格式错误
        temperature=0.1,  # 低温度 = 更稳定的结构化输出
    )

    import json
    return json.loads(response.choices[0].message.content)


def fallback_parse_resume_structure(raw_text: str) -> dict:
    """
    当 LLM 结构化阶段失败时的本地兜底解析，避免整个流程中断。
    该实现偏保守：尽量提取可用信息，其他字段保留空列表。
    """
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    joined = "\n".join(lines)

    # 简单抽取姓名：取首行中文/英文名称样式
    name = ""
    if lines:
        candidate = lines[0]
        if 1 < len(candidate) <= 30:
            name = candidate

    # 技能关键词粗提取
    skill_keywords = [
        "python", "java", "javascript", "typescript", "vue", "react", "node",
        "fastapi", "django", "flask", "mysql", "postgresql", "redis", "docker",
        "kubernetes", "git", "linux", "tensorflow", "pytorch", "pandas", "numpy",
    ]
    lower_text = joined.lower()
    skills = []
    for kw in skill_keywords:
        if kw in lower_text:
            skills.append(kw)

    # 粗略分段：按常见标题分块
    section_titles = ["教育", "教育经历", "工作经历", "实习经历", "项目", "项目经历", "技能", "个人简介"]
    sections = {title: [] for title in section_titles}
    current = None
    for line in lines:
        hit = next((t for t in section_titles if t in line), None)
        if hit:
            current = hit
            continue
        if current:
            sections[current].append(line)

    return {
        "name": name,
        "education": [{"text": " ".join(sections.get("教育", []) or sections.get("教育经历", []))}] if (sections.get("教育") or sections.get("教育经历")) else [],
        "work_experience": [{"company": "", "position": "", "responsibilities": sections.get("工作经历", []) or sections.get("实习经历", [])}] if (sections.get("工作经历") or sections.get("实习经历")) else [],
        "projects": [{"name": "", "description": " ".join(sections.get("项目", []) or sections.get("项目经历", []))}] if (sections.get("项目") or sections.get("项目经历")) else [],
        "skills": skills,
        "summary": " ".join(sections.get("个人简介", [])),
    }


def run_pdf_parser(file_bytes: bytes) -> dict:
    """
    Tool 1 对外统一入口
    Agent 调用这个函数，而不是直接调用内部函数
    """
    raw_text = extract_text_from_pdf(file_bytes)
    if not raw_text.strip():
        return {"error": "PDF 内容为空或无法解析，请检查PDF是否为扫描版"}

    # 清理潜在的坏字符，减少编码异常概率
    raw_text = raw_text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")

    try:
        structured = parse_resume_structure(raw_text)
    except UnicodeEncodeError:
        # 典型报错：'ascii' codec can't encode characters
        structured = fallback_parse_resume_structure(raw_text)
        structured["parse_warning"] = "LLM结构化阶段发生编码异常，已使用本地兜底解析"
    except Exception:
        # 其他异常也兜底，保证流程可继续
        structured = fallback_parse_resume_structure(raw_text)
        structured["parse_warning"] = "LLM结构化阶段失败，已使用本地兜底解析"

    structured["raw_text"] = raw_text  # 保留原始文本，其他工具可能用到
    return structured
