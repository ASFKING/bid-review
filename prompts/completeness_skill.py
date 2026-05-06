# prompts/completeness_skill.py
# 完整性审核 Skill——检查标书是否完整响应了所有招标要求
#
# 生活比喻：这是「消防检查员」的岗位手册——
# 不管菜品好不好吃，先确认灭火器有没有、安全出口通不通。

from prompts.structured_output_prompt import (
    build_structured_review_prompt,   # 复用已有的通用 Prompt 构建器
    get_dimension_abbreviation,       # 获取维度缩写，如 "完整性" → "CP"
)


# ===== 完整性维度的专家知识 =====
# 这些常量就是这个 Skill 的「菜谱」——定义了完整性审核要关注什么

# 维度 ID——唯一标识这个 Skill
SKILL_ID = "completeness"

# 维度名称——告诉 LLM 它在审核什么
DIMENSION_NAME = "完整性"

# 维度描述——告诉 LLM 它的职责范围
DIMENSION_DESCRIPTION = (
    "检查标书是否完整响应了招标文件的所有要求，"
    "包括但不限于：必要章节是否齐全、招标条款是否逐条响应、"
    "必填字段是否填写、附件是否完整、格式要求是否满足"
)

# 默认关注点——LLM 审核时需要重点关注的方面
DEFAULT_FOCUS_AREAS = [
    "是否缺少招标文件要求的必要章节（如技术方案、商务条款、资质证明等）",
    "是否遗漏了对招标条款的逐条响应",
    "必填字段是否有空白或缺失",
    "要求的附件、证明材料是否齐全",
    "格式要求（字体、页码、装订方式等）是否满足",
    "是否存在明显的复制粘贴痕迹（如其他项目的名称残留）",
]

# 维度缩写——用于生成 Issue ID，如 CP-001、CP-002
DIMENSION_ABBREVIATION = get_dimension_abbreviation(DIMENSION_NAME)


# ===== 核心函数：构建完整性审核 Prompt =====

def build_completeness_prompt(
    section_title: str,
    section_content: str,
    global_rules: list[str],
) -> str:
    """
    构建完整性审核的完整 Prompt

    把「完整性维度的专家知识」注入到通用 Prompt 模板中，
    生成一份可以直接发给 LLM 的审核指令。

    生活比喻：把「消防检查员的岗位知识」填入空白检查表模板，
    生成一份完整的、可直接使用的消防检查表。

    参数：
        section_title: 章节标题，如 "第三章 技术方案"
        section_content: 章节正文内容
        global_rules: 全局审核规则（从 system_config.yaml 读取）

    返回：
        完整的 Prompt 字符串，可直接发给 LLM
    """
    return build_structured_review_prompt(
        section_title=section_title,              # 章节标题
        section_content=section_content,           # 章节正文
        dimension_name=DIMENSION_NAME,             # "完整性"
        dimension_description=DIMENSION_DESCRIPTION,  # 维度描述
        focus_areas=DEFAULT_FOCUS_AREAS,           # 默认关注点列表
        global_rules=global_rules,                 # 全局规则
    )
