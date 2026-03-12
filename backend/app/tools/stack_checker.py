"""
Tool 3: 技术栈覆盖率检测
⭐ 面试考点：
   - 把 JD 要求的技能 与 简历的技能 做集合交集运算
   - 分为"已覆盖"、"缺失必须"、"缺失加分项"三类
   - 给候选人明确的补短建议
"""


def run_stack_checker(resume_data: dict, jd_analysis: dict) -> dict:
    """
    对比简历技能与JD要求的技能覆盖情况
    :param resume_data: Tool1 解析出的简历结构
    :param jd_analysis: Tool2 解析出的JD分析结果
    """
    # 简历中的所有技能（小写，方便模糊匹配）
    resume_skills = set(s.lower() for s in resume_data.get("skills", []))
    
    # 也从项目和经历中提取技术词
    for proj in resume_data.get("projects", []):
        for tech in proj.get("技术栈", "").split(","):
            resume_skills.add(tech.strip().lower())
    
    required_skills = jd_analysis.get("required_skills", [])
    preferred_skills = jd_analysis.get("preferred_skills", [])
    
    def check_skill_match(skill: str, resume_set: set) -> bool:
        """模糊匹配：'Vue.js' 能匹配 'vue3'、'vuejs'"""
        skill_lower = skill.lower().replace(".", "").replace(" ", "")
        for rs in resume_set:
            rs_clean = rs.replace(".", "").replace(" ", "")
            if skill_lower in rs_clean or rs_clean in skill_lower:
                return True
        return False
    
    covered_required = []
    missing_required = []
    for skill in required_skills:
        if check_skill_match(skill, resume_skills):
            covered_required.append(skill)
        else:
            missing_required.append(skill)
    
    covered_preferred = []
    missing_preferred = []
    for skill in preferred_skills:
        if check_skill_match(skill, resume_skills):
            covered_preferred.append(skill)
        else:
            missing_preferred.append(skill)
    
    # 计算覆盖率
    total_required = len(required_skills)
    coverage_rate = round(
        len(covered_required) / max(total_required, 1) * 100, 1
    )
    
    return {
        "coverage_rate": coverage_rate,
        "covered_required": covered_required,
        "missing_required": missing_required,
        "covered_preferred": covered_preferred,
        "missing_preferred": missing_preferred,
        "summary": f"必须技能覆盖率 {coverage_rate}%，缺失 {len(missing_required)} 项必须技能",
    }
