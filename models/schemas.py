# models/schemas.py
# 所有数据结构定义的家

from enum import Enum  # Python 内置的枚举类型
from dataclasses import dataclass, field  # 加到文件顶部的 import 区


# ===== 枚举类型：固定选项 =====

class Severity(Enum):
    """问题严重程度——只有三个选项"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class RiskLevel(Enum):
    """风险等级——用于最终报告的整体风险评估"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"

@dataclass
class TableData:
    """
    表格数据——从 Word 文档中提取的一个表格

    类比：菜品价目表——有表头（菜名、价格）、数据行（宫保鸡丁、38元）
    """
    headers: list[str]          # 表头，如 ["序号", "设备名称", "数量"]
    rows: list[list[str]]       # 数据行，每行是一个列表
    as_text: str                # 表格的文本版（给 LLM 看的）
    location: str               # 所在章节，如 "第六章 报价清单"

@dataclass
class Section:
    """
    文档章节——Word 文档中的一个章节节点

    类比：一本书的目录树——第一章下面有 1.1 节、1.2 节
    """
    title: str                        # 章节标题
    level: int                        # 标题层级 1/2/3
    content: str                      # 正文文本
    tables: list[TableData]           # 该章节内的表格
    page_range: tuple[int, int]       # 起止页码，如 (10, 15)
    children: list['Section']         # 子章节（引号是因为 Section 还没定义完）

@dataclass
class ParsedDocument:
    """
    解析后的完整文档——整个 Word 文件拆解后的结果

    类比：把一本书拆成目录树 + 全文 + 元信息
    """
    filename: str                     # 原始文件名
    total_pages: int                  # 总页数
    sections: list[Section]           # 所有章节（树状）
    full_text: str                    # 全文纯文本
    metadata: dict                    # 其他元信息

# ===== 智能层：审核配方 =====

@dataclass
class DimensionConfig:
    """
    审核维度配置——定义一个维度"检查什么、关注哪些区域"

    类比：质检员的工作手册
    """
    name: str                       # 维度名，如 "完整性"
    enabled: bool                   # 是否启用
    priority: str                   # 优先级：高/中/低
    focus_areas: list[str]          # 关注点，如 ["是否响应所有招标要求"]
    section_keywords: list[str]     # 关联章节关键词，用于定位相关章节


@dataclass
class AgentDefinition:
    """
    Agent 定义——描述一个审核 Agent 的身份

    类比：员工工牌——"我是谁、负责什么、用什么工具"
    """
    agent_id: str                   # 唯一标识，如 "completeness_agent"
    agent_name: str                 # 显示名，如 "完整性审核员"
    dimension: str                  # 负责的审核维度
    description: str                # 职责描述
    skill_id: str                   # 对应的 Skill 模板 ID


@dataclass
class ReviewRecipe:
    """
    审核配方——Analyzer 输出的"作战计划"

    类比：厨师长看完食材后写的今日菜单
    """
    industry: str                   # 行业类型，如 "软件"
    sub_industry: str               # 细分行业，如 "信息系统集成"
    confidence: float               # 行业判断置信度 0-1
    dimensions: list[DimensionConfig]      # 审核维度列表
    agent_definitions: list[AgentDefinition]  # Agent 定义列表

# ===== 智能层：审核结果 =====

@dataclass
class Issue:
    """
    单个问题——审核 Agent 发现的一个具体问题

    类比：质检员在产品上贴的"不合格标签"

    必填字段（创建时必须传）：
    - id: 问题编号，如 "CP-001"（CP = Completeness 完整性）
    - dimension: 审核维度，如 "完整性"
    - severity: 严重程度（用 Severity 枚举，不能随便填）
    - title: 一句话概括问题
    - description: 详细描述
    - evidence: 原文证据（必须引用标书原文！）
    - location: 问题位置，如 "第四章 4.2 节"
    - suggestion: 修改建议
    - confidence: 确信度 0-1，越接近 1 越确定
    - discovered_by: 谁发现的（Agent 名称）

    可选字段（有默认值，创建时可以不传）：
    - cross_verified_by: 其他 Agent 验证过这个问题
    - needs_manual_review: 是否需要人工确认
    - verification_note: 校验备注
    - hook_flags: Hook 引擎标记的问题
    """
    id: str
    dimension: str
    severity: Severity           # 注意：类型是 Severity 枚举，不是 str
    title: str
    description: str
    evidence: str
    location: str
    suggestion: str
    confidence: float
    discovered_by: str
    # 以下字段有默认值，创建时可以不传
    cross_verified_by: list[str] = field(default_factory=list)
    needs_manual_review: bool = False
    verification_note: str = ""
    hook_flags: list[str] = field(default_factory=list)

@dataclass
class ReviewResult:
    """
    单个 Agent 的审核结果——一个维度审完后产出的汇总

    类比：一个质检员的工作报告
    """
    agent_name: str                        # Agent 名称
    dimension: str                         # 审核维度
    issues: list[Issue]                    # 发现的问题列表
    summary: str                           # 一段话总结
    score: float                           # 维度评分 0-100
    risk_level: RiskLevel                  # 风险等级（用 RiskLevel 枚举）
    needs_verification: list[str]          # 需要回查验证的 issue id
    warnings: list[str] = field(default_factory=list)  # Hook 告警


@dataclass
class ValidatedResult:
    """
    校验后的结果——Validator 复查完 ReviewResult 后的输出

    类比：质检主管复查——确认了哪些是真的，哪些是误报
    """
    original: ReviewResult                 # 原始审核结果
    confirmed_issues: list[Issue]          # 确认真实的问题
    rejected_issues: list[Issue]           # 被驳回的问题（幻觉/误报）
    validation_notes: str                  # 校验备注

# ===== 智能层：最终报告 =====

@dataclass
class AuditReport:
    """
    最终审核报告——所有维度审核完后汇总的最终结果

    类比：餐厅的"食品安全总报告"——综合所有检查员的结果
    """
    document_name: str                     # 文档名称
    overall_score: float                   # 综合评分 0-100
    overall_risk: RiskLevel                # 综合风险等级
    dimension_scores: dict[str, float]     # 各维度评分，如 {"完整性": 85, "合规性": 70}
    all_issues: list[Issue]                # 所有问题汇总
    summary: str                           # 整体总结
    hook_summary: dict                     # Hook 执行统计
    checkpoint_history: list[dict]         # 检查点历史


# ===== 事件与协作层 =====

@dataclass
class ReviewEvent:
    """
    审核事件——Agent 之间通过消息总线传递的消息

    类比：服务员之间传递的纸条——"3号桌加了一道菜"
    """
    event_type: str                        # 事件类型，如 "issue.found"
    source_agent: str                      # 来源 Agent
    payload: dict                          # 事件数据
    timestamp: float                       # 时间戳


@dataclass
class CheckpointData:
    """
    检查点数据——审核流程某个时刻的完整快照

    类比：游戏存档——随时保存，随时读档
    """
    checkpoint_id: int                     # 编号（递增）
    step_name: str                         # 步骤名，如 "doc_parsed"
    timestamp: str                         # 保存时间
    state: dict                            # 完整状态数据


@dataclass
class LLMCallLog:
    """
    LLM 调用日志——记录每次调用大模型的情况

    类比：电话通话记录——谁打的、打了多久、接通没有
    """
    call_id: str                           # 调用唯一 ID
    agent_name: str                        # 调用者
    stage: str                             # 阶段（摘要/粗筛/精审/校验）
    model: str                             # 模型名称
    input_tokens: int                      # 输入 token 数
    output_tokens: int                     # 输出 token 数
    latency_ms: int                        # 耗时毫秒
    status: str                            # success/timeout/json_error/rate_limit/error
    retry_count: int                       # 重试次数
    error_message: str = ""                # 错误信息（成功时为空）




