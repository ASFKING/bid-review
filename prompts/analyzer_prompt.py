# prompts/analyzer_prompt.py
# Analyzer Agent 的 Prompt 模板——分析招标文件，生成审核配方
#
# 核心思路变了：
# 旧设计：看投标文件 → 推断行业 → 生成配方（多余操作）
# 新设计：看招标文件 → 提取要求和评分标准 → 生成精确的审核配方
#
# 生活比喻：
# 招标文件 = 考试大纲（告诉你考什么、怎么评分）
# Analyzer = 教研组（看完大纲后，安排哪些老师阅卷、每个人批改什么）


def build_tender_analysis_prompt(tender_full_text: str) -> str:
    """
    分析招标文件，提取审核要求并生成审核配方

    这是 Analyzer 的唯一一次 LLM 调用。
    招标文件包含了所有信息：行业、评分标准、资质要求、技术规格……
    不需要再从投标文件推断行业了。

    生活比喻：
    教研组拿到考试大纲后，一次会议就确定：
    - 这是数学考试（行业已知）
    - 选择题占 30 分、填空题占 20 分、大题占 50 分（评分标准）
    - 张老师批选择题、李老师批大题（Agent 分工）

    参数：
        tender_full_text: 招标文件的全文内容

    返回：
        Prompt 字符串
    """
    prompt = f"""你是一位资深的招投标审核架构师。你的任务是分析招标文件，设计一套审核方案。

## 招标文件全文
{tender_full_text}

## 你的任务

仔细阅读招标文件，完成以下两件事：

### 第一步：提取关键信息
1. **行业类型**：判断这是什么行业的招标（软件、建筑、医疗、教育等）
2. **评分标准**：招标文件中明确的评分规则和权重
3. **资质要求**：投标方必须具备的资质证书、业绩要求等
4. **技术规格**：对技术方案的具体要求
5. **商务条款**：付款方式、交货期、违约责任等
6. **必须提供的材料**：投标文件中必须包含的内容

### 第二步：设计审核方案
根据提取的信息，设计审核维度和 Agent。每个维度要根据招标文件的具体要求来配置关注点（focus_areas），而不是泛泛而谈。

## 输出要求
只输出 JSON，不要输出任何其他文字。

```json
{{
  "industry": "行业类型",
  "sub_industry": "细分行业",
  "confidence": 0.0到1.0,
  "tender_summary": "招标文件核心内容的一句话概括",
  "scoring_criteria": {{
    "total_score": 100,
    "dimensions": [
      {{"name": "技术方案", "weight": 40, "description": "评分标准描述"}},
      {{"name": "报价", "weight": 30, "description": "..."}},
      {{"name": "商务资质", "weight": 20, "description": "..."}},
      {{"name": "服务承诺", "weight": 10, "description": "..."}}
    ]
  }},
  "mandatory_requirements": [
    "必须满足的要求1（不满足则废标）",
    "必须满足的要求2"
  ],
  "dimensions": [
    {{
      "name": "完整性",
      "enabled": true,
      "priority": "高",
      "focus_areas": [
        "根据招标文件的具体要求列出，如：是否响应了第X章的技术规格",
        "不要泛泛而谈，要具体到招标文件中的条款"
      ],
      "section_keywords": ["技术方案", "投标函", "..."]
    }},
    {{
      "name": "合规性",
      "enabled": true,
      "priority": "高",
      "focus_areas": [
        "是否提供了招标文件要求的所有资质证书",
        "是否满足了招标文件规定的格式要求",
        "..."
      ],
      "section_keywords": ["资质", "证书", "..."]
    }},
    {{
      "name": "报价",
      "enabled": true,
      "priority": "中",
      "focus_areas": [
        "报价是否在预算范围内",
        "分项报价是否与总价一致",
        "..."
      ],
      "section_keywords": ["报价", "价格", "..."]
    }},
    {{
      "name": "风险",
      "enabled": true,
      "priority": "中",
      "focus_areas": [
        "是否存在偏离招标要求的条款",
        "是否承诺了难以兑现的条件",
        "..."
      ],
      "section_keywords": ["偏离", "承诺", "..."]
    }}
  ],
  "agent_definitions": [
    {{
      "agent_id": "completeness_agent",
      "agent_name": "完整性审核员",
      "dimension": "完整性",
      "description": "具体职责描述（基于招标文件内容）",
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

## 重要规则
1. focus_areas 必须基于招标文件的具体内容，不能是通用模板
2. mandatory_requirements 必须是招标文件中明确写了"必须"、"否则废标"的要求
3. scoring_criteria 必须是招标文件中明确的评分规则
4. 如果招标文件没有明确某项信息，对应字段填空列表或 null

请开始分析："""

    return prompt
