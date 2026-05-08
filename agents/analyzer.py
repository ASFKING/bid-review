# agents/analyzer.py
# Analyzer Agent——标书审核系统的"调度中心"
#
# 核心设计：
#   输入：招标文件（必须）+ 投标文件（用于后续审核）
#   输出：ReviewRecipe（基于招标文件的精确审核配方）
#
# 为什么分析招标文件而不是投标文件？
#   招标文件 = 考试大纲（告诉你考什么、怎么评分、哪些是必须的）
#   投标文件 = 考生答卷（需要对照大纲来批改）
#   先看大纲再批改，才是正确的流程。
#
# 工作流程：
#   招标文件全文 → LLM 提取要求 + 评分标准 → ReviewRecipe
#   投标文件 → 传给下游 Agent 用于审核（Analyzer 本身不分析投标文件内容）

import logging
from models.schemas import (
    ParsedDocument,
    ReviewRecipe,
    DimensionConfig,
    AgentDefinition,
    ScoringCriteria,
    ScoringDimension,
)
from infrastructure.llm_caller import LLMCaller
from prompts.analyzer_prompt import build_tender_analysis_prompt

logger = logging.getLogger(__name__)


class Analyzer:
    """
    Analyzer Agent——分析招标文件，生成审核配方

    输入：
        tender_doc: 招标文件（ParsedDocument）—— 分析对象
        bid_doc: 投标文件（ParsedDocument）—— 不分析，但记录下来供下游使用

    输出：
        ReviewRecipe —— 基于招标文件要求的精确审核配方
    """

    def __init__(self, llm_caller: LLMCaller):
        """
        初始化 Analyzer

        参数：
            llm_caller: LLM 调用包装器（用推理模型，因为分析招标文件需要深度理解）
        """
        self._llm_caller = llm_caller

    def analyze(self, tender_doc: ParsedDocument, bid_doc: ParsedDocument) -> ReviewRecipe:
        """
        分析招标文件，生成审核配方

        参数：
            tender_doc: 招标文件（分析对象）
            bid_doc: 投标文件（不分析，但记录用途）

        返回：
            ReviewRecipe 审核配方
        """
        logger.info("[Analyzer] 开始分析招标文件...")

        # ---- 第一步：调用 LLM 分析招标文件 ----
        recipe = self._analyze_tender(tender_doc)

        if recipe is None:
            logger.warning("[Analyzer] 招标文件分析失败，使用默认配方")
            return self._default_recipe()

        logger.info(
            f"[Analyzer] 分析完成：{recipe.industry} - {recipe.sub_industry}，"
            f"{len(recipe.dimensions)} 个维度，{len(recipe.agent_definitions)} 个 Agent"
        )

        return recipe

    def _analyze_tender(self, tender_doc: ParsedDocument) -> ReviewRecipe | None:
        """
        调用 LLM 分析招标文件，提取要求并生成审核配方

        参数：
            tender_doc: 招标文件

        返回：
            ReviewRecipe，失败返回 None
        """
        # 构建 Prompt：把招标文件全文传给 LLM
        prompt = build_tender_analysis_prompt(tender_doc.full_text)

        logger.info(
            f"[Analyzer] 招标文件全文长度：{len(tender_doc.full_text)} 字符，"
            f"章节：{len(tender_doc.sections)} 个"
        )

        # 调用 LLM
        result = self._llm_caller.call_json(prompt)

        if result is None:
            logger.warning("[Analyzer] LLM 调用失败")
            return None

        # 组装 ReviewRecipe
        try:
            return self._build_recipe(result)
        except Exception as e:
            logger.error(f"[Analyzer] 配方组装失败: {e}")
            return None

    def _build_recipe(self, data: dict) -> ReviewRecipe:
        """
        把 LLM 返回的 JSON 组装成 ReviewRecipe 对象

        参数：
            data: LLM 返回的 JSON dict

        返回：
            ReviewRecipe 对象
        """
        # 解析评分标准
        scoring_data = data.get("scoring_criteria", {})
        scoring_dimensions = []
        for sd in scoring_data.get("dimensions", []):
            scoring_dimensions.append(ScoringDimension(
                name=sd.get("name", "未知"),
                weight=sd.get("weight", 0),
                description=sd.get("description", ""),
            ))
        scoring_criteria = ScoringCriteria(
            total_score=scoring_data.get("total_score", 100),
            dimensions=scoring_dimensions,
        )

        # 解析审核维度配置
        dimensions = []
        for dim_data in data.get("dimensions", []):
            dim = DimensionConfig(
                name=dim_data.get("name", "未知"),
                enabled=dim_data.get("enabled", True),
                priority=dim_data.get("priority", "中"),
                focus_areas=dim_data.get("focus_areas", []),
                section_keywords=dim_data.get("section_keywords", []),
            )
            dimensions.append(dim)

        # 解析 Agent 定义
        agent_definitions = []
        for agent_data in data.get("agent_definitions", []):
            agent_def = AgentDefinition(
                agent_id=agent_data.get("agent_id", "unknown"),
                agent_name=agent_data.get("agent_name", "未知审核员"),
                dimension=agent_data.get("dimension", "未知"),
                description=agent_data.get("description", ""),
                skill_id=agent_data.get("skill_id", "unknown"),
            )
            agent_definitions.append(agent_def)

        return ReviewRecipe(
            industry=data.get("industry", "通用"),
            sub_industry=data.get("sub_industry", "通用"),
            confidence=data.get("confidence", 0.5),
            tender_summary=data.get("tender_summary", ""),
            scoring_criteria=scoring_criteria,
            mandatory_requirements=data.get("mandatory_requirements", []),
            dimensions=dimensions,
            agent_definitions=agent_definitions,
        )

    def _default_recipe(self) -> ReviewRecipe:
        """
        默认配方——当 LLM 分析失败时的兜底方案

        返回：
            包含四个默认维度的 ReviewRecipe
        """
        from config import config

        dimensions = []
        for key, dim_config in config.enabled_dimensions.items():
            dim = DimensionConfig(
                name=dim_config["name"],
                enabled=True,
                priority=dim_config.get("priority", "中"),
                focus_areas=[f"检查{dim_config['name']}相关的所有要求是否满足"],
                section_keywords=[],
            )
            dimensions.append(dim)

        default_agents = [
            AgentDefinition(
                agent_id="completeness_agent",
                agent_name="完整性审核员",
                dimension="完整性",
                description="检查投标文件是否完整响应了招标文件的所有要求",
                skill_id="completeness",
            ),
            AgentDefinition(
                agent_id="compliance_agent",
                agent_name="合规性审核员",
                dimension="合规性",
                description="检查投标文件是否符合招标文件的合规要求",
                skill_id="compliance",
            ),
            AgentDefinition(
                agent_id="price_agent",
                agent_name="报价审核员",
                dimension="报价",
                description="检查报价是否合理、计算是否正确",
                skill_id="price",
            ),
            AgentDefinition(
                agent_id="risk_agent",
                agent_name="风险审核员",
                dimension="风险",
                description="检查投标文件中的潜在风险和不利条款",
                skill_id="risk",
            ),
        ]

        return ReviewRecipe(
            industry="通用",
            sub_industry="通用",
            confidence=0.3,
            tender_summary="分析失败，使用默认配方",
            scoring_criteria=ScoringCriteria(
                total_score=100,
                dimensions=[],
            ),
            mandatory_requirements=[],
            dimensions=dimensions,
            agent_definitions=default_agents,
        )
