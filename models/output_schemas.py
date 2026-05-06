# models/output_schemas.py
# Pydantic 模型——专门用于 LLM 输出的 JSON 解析和校验
#
# 为什么需要这个？
# LLM 返回的是原始 JSON 字符串，我们需要：
# 1. 验证 JSON 结构是否正确（字段有没有、类型对不对）
# 2. 把 JSON 转成 Python 对象（方便后续代码使用）
# 3. 提供默认值（LLM 可能漏掉某些字段）
#
# 用 Java 来理解：
# - Pydantic BaseModel ≈ Java 的 DTO + @Valid 校验注解
# - Field() ≈ Java 的 @JsonProperty + @NotNull + 默认值
# - model_validate_json() ≈ Jackson 的 objectMapper.readValue()

from pydantic import BaseModel, Field
from typing import Optional


class IssueOutput(BaseModel):
    """
    LLM 输出的单个问题结构

    这个类定义了 LLM 必须返回的 JSON 格式。
    Pydantic 会自动做以下事情：
    1. 检查必填字段是否存在
    2. 检查字段类型是否正确
    3. 把 JSON 字符串自动转成 Python 对象

    类比：这是一张"问题报告单"的模板——
    LLM 必须按这个模板填写，缺了哪项、填错了类型，都会被拦住。

    注意：severity 用字符串 "高"/"中"/"低"，而不是枚举。
    为什么？因为 LLM 返回的是 JSON，JSON 里没有"枚举"的概念。
    我们在解析后再转成 Severity 枚举。
    """

    # ===== 必填字段 =====

    id: str = Field(
        ...,  # ... 表示必填
        description="问题编号，格式：维度缩写-序号，如 CP-001（CP=完整性）、CM-001（CM=合规性）"
    )

    dimension: str = Field(
        ...,
        description="审核维度：完整性、合规性、报价、风险"
    )

    severity: str = Field(
        ...,
        description="严重程度：高、中、低"
    )

    title: str = Field(
        ...,
        description="一句话概括问题，不超过 30 字"
    )

    description: str = Field(
        ...,
        description="详细描述问题，说明为什么这是个问题"
    )

    evidence: str = Field(
        ...,
        description="引用标书原文作为证据，必须是原文摘录，不能改写"
    )

    location: str = Field(
        ...,
        description="问题所在位置，如 '第三章 3.1 节' 或 '报价清单表格'"
    )

    suggestion: str = Field(
        ...,
        description="具体的修改建议，告诉投标方怎么改"
    )

    confidence: float = Field(
        ...,
        ge=0.0,  # 最小值 0
        le=1.0,  # 最大值 1
        description="置信度 0-1，表示你对这个问题的确信程度。1.0 = 非常确定"
    )

    discovered_by: str = Field(
        ...,
        description="发现问题的 Agent 名称，如 '完整性审核员'"
    )

    # ===== 可选字段（有默认值） =====

    needs_manual_review: bool = Field(
        default=False,
        description="是否需要人工确认。confidence < 0.7 时设为 true"
    )

    verification_note: str = Field(
        default="",
        description="校验备注，说明为什么需要人工确认"
    )


class IssueListOutput(BaseModel):
    """
    LLM 输出的问题列表

    为什么包一层？
    因为 LLM 返回的 JSON 通常有两种格式：
    1. 直接返回数组：[{...}, {...}]
    2. 返回一个对象，数组在某个字段里：{"issues": [{...}, {...}]}

    我们用这个类来处理第 2 种情况。
    如果 LLM 返回的是纯数组，我们会在调用时做特殊处理。
    """

    issues: list[IssueOutput] = Field(
        default_factory=list,
        description="发现的问题列表"
    )