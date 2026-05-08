# agents/review_agent.py
# ReviewAgent 基类——标书审核的核心执行者
#
# 生活比喻：服务员——看菜单、写点菜单、打电话给后厨、整理订单
#
# 工作流程：
#   章节 → Skill 构建 Prompt → 调用 LLM → output_parser 解析 → IssueOutput → 转换为 Issue → 汇总

import logging                                    # 日志记录
from models.schemas import (                      # 内部业务模型
    Section, Issue, Severity,
    ReviewResult, RiskLevel,
)
from models.output_schemas import IssueOutput      # LLM 输出 DTO
from infrastructure.llm_caller import LLMCaller   # LLM 调用包装器
from infrastructure.output_parser import (         # 复用已有的解析器
    parse_issue_list_output,
)

logger = logging.getLogger(__name__)


# ===== 转换函数：IssueOutput → Issue =====

def _output_to_issue(output: IssueOutput, agent_name: str, id_prefix: str, counter: int) -> Issue:
    """
    把 LLM 输出的 IssueOutput（Pydantic DTO）转换为系统内部的 Issue（dataclass）

    生活比喻：把后厨手写的潦草订单，整理成标准格式的打印订单

    为什么需要这一步？
    - IssueOutput 用字符串 severity（"高"/"中"/"低"），因为 LLM 只能返回字符串
    - Issue 用枚举 Severity，因为内部代码用枚举更安全
    - Issue 有 cross_verified_by、hook_flags 等后期协作字段，IssueOutput 没有

    参数：
        output: LLM 输出解析后的 IssueOutput 对象
        agent_name: Agent 名称（填入 discovered_by）
        id_prefix: Issue ID 前缀，如 "CP"
        counter: 当前序号，用于生成 Issue ID

    返回：
        Issue 对象
    """
    # 解析严重程度：字符串 → 枚举
    severity_map = {"高": Severity.HIGH, "中": Severity.MEDIUM, "低": Severity.LOW}
    severity = severity_map.get(output.severity, Severity.LOW)

    # 确保置信度在合法范围
    confidence = max(0.0, min(1.0, output.confidence))

    return Issue(
        id=f"{id_prefix}-{counter:03d}",         # 自动生成 ID
        dimension=output.dimension,                # 维度名
        severity=severity,                         # 枚举
        title=output.title,                        # 问题标题
        description=output.description,            # 详细描述
        evidence=output.evidence,                  # 原文证据
        location=output.location,                  # 位置
        suggestion=output.suggestion,              # 修改建议
        confidence=confidence,                     # 置信度
        discovered_by=output.discovered_by or agent_name,  # 发现者
        needs_manual_review=confidence < 0.7,      # 低置信度需人工确认
        # 以下字段由后期模块填充，这里给默认值
        cross_verified_by=[],
        hook_flags=[],
    )


class ReviewAgent:
    """
    审核 Agent 基类——执行单维度的标书审核

    生活比喻：服务员——负责把客人点的菜（章节）送到后厨（LLM），
    然后把做好的菜（Issue 列表）端回来。

    数据流转：
    Section → Prompt → LLM → JSON → output_parser → [IssueOutput] → 转换 → [Issue] → ReviewResult
    """

    def __init__(
        self,
        agent_name: str,                    # Agent 名称，如 "完整性审核员"
        dimension: str,                     # 审核维度，如 "完整性"
        skill_builder: callable,            # Skill 的 Prompt 构建函数
        llm_caller: LLMCaller,              # LLM 调用包装器
        id_prefix: str = "XX",              # Issue ID 前缀，如 "CP"
    ):
        self._agent_name = agent_name
        self._dimension = dimension
        self._skill_builder = skill_builder
        self._llm_caller = llm_caller
        self._id_prefix = id_prefix
        self._issue_counter = 0

    def _next_counter(self) -> int:
        """递增并返回问题计数器"""
        self._issue_counter += 1
        return self._issue_counter

    def review_section(self, section: Section, global_rules: list[str]) -> list[Issue]:
        """
        审核单个章节，返回 Issue 列表

        流程：
        1. Skill 构建 Prompt
        2. LLMCaller 调用 LLM，返回 dict
        3. output_parser 解析 dict → [IssueOutput]
        4. 转换 [IssueOutput] → [Issue]

        参数：
            section: 要审核的章节
            global_rules: 全局审核规则

        返回：
            该章节发现的 Issue 列表（可能为空）
        """
        # ---- 第一步：Skill 构建 Prompt ----
        prompt = self._skill_builder(
            section_title=section.title,
            section_content=section.content,
            global_rules=global_rules,
        )
        print(prompt)
        logger.info(f"[{self._agent_name}] 开始审核章节：{section.title[:50]}...")

        # ---- 第二步：调用 LLM，拿到 dict ----
        raw_result = self._llm_caller.call_json(prompt)

        if raw_result is None:
            logger.warning(
                f"[{self._agent_name}] 章节 '{section.title[:30]}' 的 LLM 调用失败，跳过"
            )
            return []

        # ---- 第三步：复用 output_parser 解析 dict → [IssueOutput] ----
        issue_outputs = parse_issue_list_output(raw_result)

        if not issue_outputs:
            logger.info(f"[{self._agent_name}] 章节 '{section.title[:30]}' 未发现问题")
            return []

        # ---- 第四步：[IssueOutput] → [Issue] ----
        issues = []
        for output in issue_outputs:
            counter = self._next_counter()
            issue = _output_to_issue(
                output=output,
                agent_name=self._agent_name,
                id_prefix=self._id_prefix,
                counter=counter,
            )
            issues.append(issue)

        logger.info(
            f"[{self._agent_name}] 章节 '{section.title[:30]}' 审核完成，"
            f"发现 {len(issues)} 个问题"
        )

        return issues

    def review_document(
        self,
        sections: list[Section],
        global_rules: list[str],
    ) -> ReviewResult:
        """
        审核整个文档，汇总返回 ReviewResult

        参数：
            sections: 文档的所有章节（平铺列表）
            global_rules: 全局审核规则

        返回：
            完整的审核结果
        """
        all_issues: list[Issue] = []

        # 遍历所有章节（含递归子章节）
        for section in sections:
            issues = self.review_section(section, global_rules)
            all_issues.extend(issues)
            if section.children:
                all_issues.extend(self._review_children(section.children, global_rules))

        # 组装 ReviewResult
        return ReviewResult(
            agent_name=self._agent_name,
            dimension=self._dimension,
            issues=all_issues,
            summary=self._build_summary(all_issues),
            score=self._calculate_score(all_issues),
            risk_level=self._assess_risk(all_issues),
            needs_verification=[i.id for i in all_issues if i.needs_manual_review],
        )

    def _review_children(self, children: list[Section], global_rules: list[str]) -> list[Issue]:
        """递归审核子章节"""
        issues = []
        for child in children:
            issues.extend(self.review_section(child, global_rules))
            if child.children:
                issues.extend(self._review_children(child.children, global_rules))
        return issues

    def _build_summary(self, issues: list[Issue]) -> str:
        """根据问题列表生成文字总结"""
        if not issues:
            return f"【{self._dimension}审核】未发现问题，该维度表现良好。"

        high = sum(1 for i in issues if i.severity == Severity.HIGH)
        medium = sum(1 for i in issues if i.severity == Severity.MEDIUM)
        low = sum(1 for i in issues if i.severity == Severity.LOW)

        parts = [f"【{self._dimension}审核】共发现 {len(issues)} 个问题："]
        if high:
            parts.append(f"  - 高严重度：{high} 个")
        if medium:
            parts.append(f"  - 中严重度：{medium} 个")
        if low:
            parts.append(f"  - 低严重度：{low} 个")
        return "\n".join(parts)

    def _calculate_score(self, issues: list[Issue]) -> float:
        """根据问题列表计算维度评分"""
        from config import config

        base_score = config.scoring.get("base_score", 100)
        deduction_map = config.scoring.get("severity_deduction", {"高": 15, "中": 5, "低": 1})

        score = float(base_score)
        for issue in issues:
            score -= deduction_map.get(issue.severity.value, 1)

        return max(0.0, score)

    def _assess_risk(self, issues: list[Issue]) -> RiskLevel:
        """根据问题列表评估风险等级"""
        has_high = any(i.severity == Severity.HIGH for i in issues)
        medium_count = sum(1 for i in issues if i.severity == Severity.MEDIUM)

        if has_high or medium_count >= 3:
            return RiskLevel.HIGH
        elif medium_count > 0:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
