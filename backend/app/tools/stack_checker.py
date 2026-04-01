"""Tool 3: compare resume skills against JD requirements.

输入：
- resume_data（来自 pdf_parser）
- jd_analysis（来自 jd_matcher）

输出：
- 必须/加分技能的覆盖与缺失清单
- 覆盖率指标（coverage_rate）
"""
import re

# 中英文技能别名表：key 是规范名（小写无符号），value 是同义词集合。
# 匹配时简历词和 JD 词都会先映射到规范名再比较，避免别名误判。
_SKILL_ALIASES: dict[str, set[str]] = {
    "javascript": {"js", "javascript", "ecmascript", "es6", "es2015"},
    "typescript": {"ts", "typescript"},
    "python":     {"python", "python3", "py"},
    "java":       {"java", "jdk"},
    "golang":     {"go", "golang"},
    "csharp":     {"c#", "csharp", "dotnet", ".net", "net"},
    "cpp":        {"c++", "cpp", "cplusplus"},
    "vue":        {"vue", "vuejs", "vue2", "vue3", "vue.js"},
    "react":      {"react", "reactjs", "react.js", "reactnative", "react native"},
    "angular":    {"angular", "angularjs", "angular.js"},
    "nodejs":     {"node", "nodejs", "node.js"},
    "nextjs":     {"next", "nextjs", "next.js"},
    "nuxtjs":     {"nuxt", "nuxtjs", "nuxt.js"},
    "springboot": {"spring", "springboot", "spring boot", "springframework"},
    "fastapi":    {"fastapi", "fast api"},
    "django":     {"django"},
    "flask":      {"flask"},
    "mysql":      {"mysql", "mariadb"},
    "postgresql": {"postgresql", "postgres", "pg"},
    "mongodb":    {"mongodb", "mongo"},
    "redis":      {"redis"},
    "elasticsearch": {"elasticsearch", "es", "elastic"},
    "docker":     {"docker", "dockerfile"},
    "kubernetes": {"kubernetes", "k8s", "kubectl"},
    "git":        {"git", "github", "gitlab", "gitflow"},
    "linux":      {"linux", "unix", "centos", "ubuntu"},
    "tensorflow": {"tensorflow", "tf"},
    "pytorch":    {"pytorch", "torch"},
    "pandas":     {"pandas"},
    "numpy":      {"numpy", "np"},
    # 中文常见技能别名
    "机器学习":   {"机器学习", "ml", "machine learning"},
    "深度学习":   {"深度学习", "dl", "deep learning"},
    "数据分析":   {"数据分析", "data analysis", "数据挖掘"},
    "项目管理":   {"项目管理", "pmp", "project management"},
}

# 规范化后 token → 规范 key 的反查表（构建一次，查询 O(1)）
_ALIAS_LOOKUP: dict[str, str] = {}
for _canonical, _aliases in _SKILL_ALIASES.items():
    for _a in _aliases:
        _ALIAS_LOOKUP[_a] = _canonical


def _normalize(token: str) -> str:
    """
    把技能词规范化：小写 → 去空格/符号 → 查别名表。
    返回规范名（如有）或清洗后的原始词。
    """
    cleaned = token.lower().strip()
    stripped = re.sub(r"[\s.\-_/]", "", cleaned)
    return _ALIAS_LOOKUP.get(stripped, _ALIAS_LOOKUP.get(cleaned, stripped))


def _extract_tech_tokens(text: str) -> set[str]:
    """
    从技术栈字符串里提取词汇。
    支持中英文逗号、顿号、斜杠、空格等分隔符，并过滤空字符串。
    """
    parts = re.split(r"[,，、/\s]+", text)
    return {_normalize(p) for p in parts if p.strip()}


def _collect_resume_skills(resume_data: dict) -> set[str]:
    """
    聚合简历里所有技能词，来源：
    1. skills 主字段
    2. 项目技术栈字段（兼容中英文字段名和多种分隔符）
    3. 工作经历 responsibilities 里的英文技术 token
    """
    skills: set[str] = set()

    # 来源 1：skills 主字段
    for s in resume_data.get("skills", []):
        if isinstance(s, str) and s.strip():
            skills.add(_normalize(s))

    # 来源 2：项目技术栈（兼容中英文字段名）
    for proj in resume_data.get("projects", []):
        for field in ("技术栈", "tech_stack", "technologies", "stack"):
            raw = proj.get(field, "")
            if raw:
                skills.update(_extract_tech_tokens(str(raw)))

    # 来源 3：工作经历职责描述里提取长度 ≥ 2 的英文 token
    for exp in resume_data.get("work_experience", []):
        for resp in exp.get("responsibilities", []):
            for token in re.findall(r"[A-Za-z][A-Za-z0-9\+\#\.]{1,20}", str(resp)):
                skills.add(_normalize(token))

    skills.discard("")
    return skills


def _skill_matched(jd_skill: str, resume_norms: set[str]) -> bool:
    """
    判断单个 JD 技能是否被简历覆盖。
    匹配逻辑（按优先级）：
    1. 规范名完全相等（最可靠）
    2. 子串包含，但双方长度都 ≥ 2，防止单字母误判
       （处理版本号后缀，如 vue → vue3）
    """
    jd_norm = _normalize(jd_skill)
    if not jd_norm:
        return False

    if jd_norm in resume_norms:
        return True

    for rn in resume_norms:
        if len(jd_norm) < 2 or len(rn) < 2:
            continue
        shorter, longer = (jd_norm, rn) if len(jd_norm) <= len(rn) else (rn, jd_norm)
        if shorter in longer:
            return True

    return False


def run_stack_checker(resume_data: dict, jd_analysis: dict) -> dict:
    """
    对比简历技能与JD要求的技能覆盖情况。
    :param resume_data: Tool1 解析出的简历结构
    :param jd_analysis: Tool2 解析出的JD分析结果
    """
    resume_norms = _collect_resume_skills(resume_data)

    # 过滤空字符串，避免空条目污染统计
    required_skills  = [s for s in jd_analysis.get("required_skills", [])  if isinstance(s, str) and s.strip()]
    preferred_skills = [s for s in jd_analysis.get("preferred_skills", []) if isinstance(s, str) and s.strip()]

    covered_required, missing_required = [], []
    for skill in required_skills:
        (covered_required if _skill_matched(skill, resume_norms) else missing_required).append(skill)

    covered_preferred, missing_preferred = [], []
    for skill in preferred_skills:
        (covered_preferred if _skill_matched(skill, resume_norms) else missing_preferred).append(skill)

    # required_skills 为空时返回 None，避免用 100% 误导报告
    if not required_skills:
        coverage_rate = None
        summary = "JD未指定必须技能，暂无覆盖率"
    else:
        coverage_rate = round(len(covered_required) / len(required_skills) * 100, 1)
        summary = f"必须技能覆盖率 {coverage_rate}%，缺失 {len(missing_required)} 项必须技能"

    return {
        "coverage_rate": coverage_rate,
        "covered_required": covered_required,
        "missing_required": missing_required,
        "covered_preferred": covered_preferred,
        "missing_preferred": missing_preferred,
        "summary": summary,
    }
