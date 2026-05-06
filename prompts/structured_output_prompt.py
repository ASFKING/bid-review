# prompts/structured_output_prompt.py
# 结构化输出的 Prompt 模板
#
# 核心思想：
# LLM 就像一个非常听话但有点"直脑筋"的员工。
# 你给它一张表格模板，它就会照着填。
# 但如果你只说"帮我分析一下"，它就自由发挥，返回的格式每次都不同。
#
# 所以我们需要：
# 1. 明确告诉它：你扮演什么角色
# 2. 明确告诉它：你要做什么任务
# 3. 明确告诉它：输出必须是什么格式（JSON Schema）
# 4. 给它一个示例（Few-shot），让它知道"长什么样"


def build_structured_review_prompt(
    section_title: str,
    section_content: str,
    dimension_name: str,
    dimension_description: str,
    focus_areas: list[str],
    global_rules: list[str],
) -> str:
    """
    构建结构化审核的 Prompt

    参数：
        section_title: 章节标题，如 "第三章 技术方案"
        section_content: 章节正文内容
        dimension_name: 审核维度名，如 "完整性"
        dimension_description: 维度描述，如 "检查标书是否完整响应了所有招标要求"
        focus_areas: 关注点列表，如 ["是否响应所有招标要求", "是否缺少必要附件"]
        global_rules: 全局审核规则

    返回：
        完整的 Prompt 字符串
    """

    # 把关注点列表转成编号文本
    focus_text = "\n".join(f"  {i+1}. {area}" for i, area in enumerate(focus_areas))

    # 把全局规则列表转成编号文本
    rules_text = "\n".join(f"  - {rule}" for rule in global_rules)

    # Prompt 模板——用三段式：角色 + 任务 + 输出格式
    prompt = f"""你是一位资深的标书审核专家，专门负责「{dimension_name}」维度的审核。

## 你的角色
- 身份：{dimension_name}审核员
- 职责：{dimension_description}

## 审核任务
请对以下标书章节进行{dimension_name}审核：

### 章节标题
{section_title}

### 章节内容
{section_content}

## 关注重点
请重点关注以下方面：
{focus_text}

## 全局审核规范（必须遵守）
{rules_text}

## 输出格式要求
你必须严格按照以下 JSON 格式输出结果。不要输出任何其他文字，只输出 JSON。

输出一个 JSON 对象，包含一个 "issues" 数组，每个问题的格式如下：

```json
{{
  "issues": [
    {{
      "id": "维度缩写-序号，如 CP-001",
      "dimension": "{dimension_name}",
      "severity": "高/中/低",
      "title": "一句话概括问题（不超过30字）",
      "description": "详细描述问题",
      "evidence": "引用标书原文作为证据",
      "location": "问题所在位置",
      "suggestion": "具体的修改建议",
      "confidence": 0.0到1.0之间的数字,
      "discovered_by": "{dimension_name}审核员"
    }}
  ]
}}
```

## 重要规则
1. 只报告有明确证据的问题，禁止猜测
2. evidence 必须是标书原文摘录，不能改写
3. confidence 反映你的确信程度：0.9+非常确定，0.7-0.9比较确定，0.7以下需要人工确认
4. 如果该章节没有发现问题，返回空数组：{{"issues": []}}
5. severity 判断标准：
   - 高：缺失关键内容、违反强制性要求、可能导致废标
   - 中：内容不完整、格式不规范、可能影响评分
   - 低：表述可优化、建议性改进

请开始审核，只输出 JSON："""

    return prompt


# ===== 维度缩写映射（用于生成 Issue ID） =====
DIMENSION_ABBREVIATIONS = {
    "完整性": "CP",   # Completeness
    "合规性": "CM",   # Compliance
    "报价": "PR",     # Price
    "风险": "RS",     # Risk
}


def get_dimension_abbreviation(dimension_name: str) -> str:
    """
    获取维度的缩写（用于 Issue ID）

    如：get_dimension_abbreviation("完整性") → "CP"
    """
    return DIMENSION_ABBREVIATIONS.get(dimension_name, "XX")