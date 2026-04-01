"""Tool 1: parse resume PDF into structured fields.

该工具分两层：
1) PDF 文本提取（pdfplumber）；
2) LLM 结构化解析（严格模式，失败直接抛错）。
"""
import pdfplumber
import io
from openai import OpenAI
from app.core.config import get_settings

settings = get_settings()

# OpenAI-compatible client configured via settings.
client = OpenAI(
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    从 PDF 字节流提取原始文本
    :param file_bytes: 上传文件的字节内容
    :return: 提取的纯文本
    """
    # 按页提取，合并为单一长文本供后续结构化。
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            # 提取普通文本
            text = page.extract_text()
            if text:
                text_parts.append(text)
            # 同时提取表格，避免技能/项目信息只存在表格里而丢失。
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    row_text = " | ".join(cell or "" for cell in row)
                    text_parts.append(row_text)
    return "\n".join(text_parts)


def parse_resume_structure(raw_text: str) -> dict:
    """
    用 LLM 把原始文本解析成结构化简历数据。
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

    # 要求模型直接返回 JSON，降低后处理复杂度与解析失败概率。
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    import json
    return json.loads(response.choices[0].message.content)


def run_pdf_parser(file_bytes: bytes) -> dict:
    """
    Tool 1 对外统一入口（Agent 仅依赖这个入口）。

    约定返回：
    - 成功：结构化 dict，并附带 raw_text；
    - 失败：返回 {"error": "..."}，由上层 Agent 决定是否终止流程。
    """
    raw_text = extract_text_from_pdf(file_bytes)
    if not raw_text.strip():
        # 常见于扫描版 PDF（图像文本），当前链路未启用 OCR 时会命中这里。
        return {"error": "PDF 内容为空或无法解析，请检查PDF是否为扫描版"}

    # 清理潜在坏字符，减少下游 LLM/日志/传输中的编码异常概率。
    raw_text = raw_text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")

    # 严格模式：结构化失败直接抛异常，由上层 Agent 终止并展示失败信息。
    structured = parse_resume_structure(raw_text)

    # 保留原始文本：便于调试、追问、以及后续可能新增的分析工具复用。
    structured["raw_text"] = raw_text
    return structured
