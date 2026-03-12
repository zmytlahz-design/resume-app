"""
Tool 4: STAR 法则检测器
⭐ 面试考点：
   STAR = Situation(背景) + Task(任务) + Action(行动) + Result(结果)
   优秀的简历项目描述必须包含这四个要素
   
   为什么让 LLM 来判断而不用规则？
   - 自然语言表达方式太多样，规则覆盖不全
   - LLM 理解语义，判断更准确
   - 这是 LLM 最擅长的：语义理解类任务
"""
from openai import OpenAI
from app.core.config import get_settings

settings = get_settings()
client = OpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
)


def check_single_experience(experience_text: str, exp_title: str) -> dict:
    """检查单条经历是否符合STAR法则"""
    prompt = f"""分析以下简历经历描述，检查是否包含STAR法则的四个要素。

STAR法则：
- S (Situation/背景): 描述了项目/任务的背景是什么
- T (Task/任务): 描述了你负责什么、目标是什么  
- A (Action/行动): 描述了你具体做了什么（用数据/技术细节）
- R (Result/结果): 描述了量化的结果/成果（如：提升XX%、节省XX小时）

经历标题：{exp_title}
经历描述：{experience_text}

以JSON返回分析结果：
{{
  "has_situation": true/false,
  "has_task": true/false,
  "has_action": true/false,
  "has_result": true/false,
  "result_is_quantified": true/false,
  "star_score": 0-10的评分,
  "missing_elements": ["缺少的要素说明"],
  "improvement_hint": "一句话改进建议"
}}"""

    response = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    import json
    return json.loads(response.choices[0].message.content)


def run_star_checker(resume_data: dict) -> dict:
    """
    Tool 4 对外统一入口
    检查所有工作经历和项目的STAR法则完整性
    """
    results = []
    
    # 检查工作/实习经历
    for exp in resume_data.get("work_experience", []):
        description = "\n".join(exp.get("responsibilities", []))
        if description.strip():
            title = f"{exp.get('company', '')} - {exp.get('position', '')}"
            check = check_single_experience(description, title)
            check["title"] = title
            check["type"] = "工作经历"
            results.append(check)
    
    # 检查项目经历
    for proj in resume_data.get("projects", []):
        description = proj.get("描述", "") or proj.get("description", "")
        if description.strip():
            title = proj.get("项目名", "") or proj.get("name", "项目")
            check = check_single_experience(description, title)
            check["title"] = title
            check["type"] = "项目经历"
            results.append(check)
    
    if not results:
        return {"error": "未找到可检查的经历描述", "results": []}
    
    avg_score = round(sum(r.get("star_score", 0) for r in results) / len(results), 1)
    
    return {
        "overall_star_score": avg_score,
        "checked_count": len(results),
        "results": results,
        "summary": f"检查了 {len(results)} 条经历，STAR平均得分 {avg_score}/10",
    }
