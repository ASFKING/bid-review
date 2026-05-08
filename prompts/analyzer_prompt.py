# prompts/analyzer_prompt.py
# Analyzer Agent 的 Prompt 模板——行业分析 + 配方生成
#
# 生活比喻：
# 第一次调用 = 服务员看客人穿什么衣服，判断是商务宴请还是朋友聚餐
# 第二次调用 = 厨师长根据聚餐类型，安排今天的菜单和人手分工


def build_industry_analysis_prompt(section_titles: list[str]) -> str:
    """
    第一次 LLM 调用：分析投标文件所属行业

    为什么只需要标题？
    就像你判断一家餐厅是什么菜系，看菜单标题就够了——
    "宫保鸡丁"是中餐，"寿司拼盘"是日料。
    不需要把每道菜都吃一遍。

    参数：
        section_titles: 投标文件的所有章节标题（平铺列表）

    返回：
        Prompt 字符串
    """
    # 把标题列表格式化成编号文本
    titles_text = "\n".join(f"  {i+1}. {title}" for i, title in enumerate(section_titles))

    prompt = f"""你是一位资深的招投标行业专家，能通过投标文件的目录结构快速判断所属行业。

## 任务
分析以下投标文件的章节标题，判断它属于什么行业。

## 章节标题
{titles_text}

## 输出要求
只输出 JSON，不要输出任何其他文字。

```json
{{
  "industry": "行业大类，如：软件、建筑、医疗、教育、物流、制造",
  "sub_industry": "细分行业，如：信息系统集成、土建工程、医疗设备采购",
  "confidence": 0.0到1.0之间的置信度,
  "reasoning": "判断依据，简要说明从哪些标题看出的"
}}
```

请开始分析："""

    return prompt


def build_recipe_generation_prompt(
    industry: str,
    sub_industry: str,
    section_titles: list[str],
    available_dimensions: dict[str, dict],
) -> str:
    """
    第二次 LLM 调用：根据行业生成审核配方

    生活比喻：
    厨师长知道今天是"商务宴请"后，决定：
    - 需要几个服务员？（几个 Agent）
    - 每个服务员负责什么？（审核维度）
    - 每个人重点关注什么？（focus_areas）

    参数：
        industry: 行业大类，如 "软件"
        sub_industry: 细分行业，如 "信息系统集成"
        section_titles: 投标文件的章节标题列表
        available_dimensions: 可用的审核维度配置（从 system_config.yaml 读取）

    返回：
        Prompt 字符串
    """
    titles_text = "\n".join(f"  {i+1}. {title}" for i, title in enumerate(section_titles))

    # 把可用维度格式化成说明文本
    dim_lines = []
    for key, dim in available_dimensions.items():
        dim_lines.append(f"  - {key}（{dim['name']}）：优先级 {dim['priority']}")
    dimensions_text = "\n".join(dim_lines)

    prompt = f"""你是一位资深的标书审核架构师，负责为标书审核系统设计审核方案。

## 背景
已判断该投标文件属于：{industry} - {sub_industry}

## 投标文件章节标题
{titles_text}

## 可用的审核维度
{dimensions_text}

## 任务
根据投标文件的行业类型和章节结构，设计一套审核方案，包括：
1. 为每个启用的审核维度配置关注点（focus_areas）和关联章节关键词（section_keywords）
2. 为每个审核维度定义一个 Agent

## 设计原则
- focus_areas：根据该行业的特点，列出该维度需要重点关注的方面（3-6 个）
- section_keywords：列出与该维度相关的章节标题关键词（用于后续定位相关章节）
- 每个 Agent 要有清晰的职责描述

## 输出要求
只输出 JSON，不要输出任何其他文字。

```json
{{
  "dimensions": [
    {{
      "name": "完整性",
      "enabled": true,
      "priority": "高",
      "focus_areas": ["该行业特有的关注点1", "关注点2", "..."],
      "section_keywords": ["技术方案", "资质", "..."]
    }},
    {{
      "name": "合规性",
      "enabled": true,
      "priority": "高",
      "focus_areas": ["..."],
      "section_keywords": ["..."]
    }},
    {{
      "name": "报价",
      "enabled": true,
      "priority": "中",
      "focus_areas": ["..."],
      "section_keywords": ["报价", "价格", "..."]
    }},
    {{
      "name": "风险",
      "enabled": true,
      "priority": "中",
      "focus_areas": ["..."],
      "section_keywords": ["..."]
    }}
  ],
  "agent_definitions": [
    {{
      "agent_id": "completeness_agent",
      "agent_name": "完整性审核员",
      "dimension": "完整性",
      "description": "该 Agent 的具体职责描述",
      "skill_id": "completeness"
    }},
    {{
      "agent_id": "compliance_agent",
      "agent_name": "合规性审核员",
      "dimension": "合规性",
      "description": "...",
      "skill_id": "compliance"
    }},
    {{
      "agent_id": "price_agent",
      "agent_name": "报价审核员",
      "dimension": "报价",
      "description": "...",
      "skill_id": "price"
    }},
    {{
      "agent_id": "risk_agent",
      "agent_name": "风险审核员",
      "dimension": "风险",
      "description": "...",
      "skill_id": "risk"
    }}
  ]
}}
```

请开始设计："""

    return prompt
