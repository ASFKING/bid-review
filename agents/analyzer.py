# agents/analyzer.py
# Analyzer Agent——标书审核系统的"调度中心"
#
# 生活比喻：餐厅里的前台接待——
# 1. 看客人穿什么衣服，判断是商务宴请还是朋友聚餐（行业分析）
# 2. 根据聚餐类型，安排今天的菜单和人手分工（生成审核配方）
#
# 工作流程：
#   ParsedDocument → 提取标题 → LLM 分析行业 → LLM 生成配方 → ReviewRecipe

import logging                                     # 日志记录
from models.schemas import (                       # 数据结构
    ParsedDocument,
    ReviewRecipe,
    DimensionConfig,
    AgentDefinition,
)
from infrastructure.llm_caller import LLMCaller    # LLM 调用包装器
from prompts.analyzer_prompt import (               # Prompt 模板
    build_industry_analysis_prompt,
    build_recipe_generation_prompt,
)

logger = logging.getLogger(__name__)


class Analyzer:
    """
    Analyzer Agent——分析文档行业类型，生成审核配方

    为什么需要它？
    不同行业的标书审核重点不同：
    - 软件标关注技术方案、团队资质
    - 建筑标关注安全资质、施工方案
    - 医疗标关注设备认证、临床数据
    Analyzer 让系统能"看一眼标书就知道该怎么审"。

    技术上做两次 LLM 调用：
    第一次：看标题 → 判断行业
    第二次：根据行业 → 生成审核维度配置和 Agent 定义
    """

    def __init__(self, llm_caller: LLMCaller):
        """
        初始化 Analyzer

        参数：
            llm_caller: LLM 调用包装器（通常用推理模型，因为分析需要"动脑子"）
        """
        self._llm_caller = llm_caller

    def analyze(self, document: ParsedDocument) -> ReviewRecipe:
        """
        分析文档，生成审核配方

        这是 Analyzer 的核心方法，完整流程：
        1. 从文档中提取章节标题
        2. 调用 LLM 分析行业类型
        3. 调用 LLM 生成审核配方
        4. 组装并返回 ReviewRecipe

        参数：
            document: 解析后的文档对象

        返回：
            ReviewRecipe 审核配方
        """
        # ---- 第一步：提取章节标题 ----
        section_titles = self._extract_titles(document.sections)
        logger.info(f"[Analyzer] 提取到 {len(section_titles)} 个章节标题")

        # ---- 第一次 LLM 调用：分析行业类型 ----
        industry_result = self._analyze_industry(section_titles)
        if industry_result is None:
            logger.warning("[Analyzer] 行业分析失败，使用默认配方")
            return self._default_recipe()

        # ---- 第二次 LLM 调用：生成审核配方 ----
        recipe = self._generate_recipe(industry_result, section_titles)
        if recipe is None:
            logger.error("[Analyzer] 配方生成失败，使用默认配方")
            return self._default_recipe()

        logger.info(
            f"[Analyzer] 配方生成成功：{recipe.industry} - {recipe.sub_industry}，"
            f"{len(recipe.dimensions)} 个维度，{len(recipe.agent_definitions)} 个 Agent"
        )

        return recipe

    def _extract_titles(self, sections: list) -> list[str]:
        """
        递归提取所有章节标题

        生活比喻：把一棵树的所有叶子摘下来，放到一个篮子里。
        不管叶子在哪个枝头（第几层），统统摘下来。

        参数：
            sections: 章节列表（可能有嵌套的 children）

        返回：
            平铺的标题列表
        """
        titles = []
        for section in sections:
            titles.append(section.title)
            if section.children:
                titles.extend(self._extract_titles(section.children))
        return titles

    def _analyze_industry(self, section_titles: list[str]) -> dict:
        """
        第一次 LLM 调用：分析文档行业类型

        参数：
            section_titles: 章节标题列表

        返回：
            行业分析结果 dict，如 {"industry": "软件", "sub_industry": "信息系统集成", ...}
        """
        prompt = build_industry_analysis_prompt(section_titles)
        logger.info("[Analyzer] 开始行业分析...")

        result = self._llm_caller.call_json(prompt)

        if result is None:
            logger.warning("[Analyzer] 行业分析 LLM 调用失败")
            return None

        # 基本校验：确保返回了必要字段
        if "industry" not in result:
            logger.warning(f"[Analyzer] 行业分析结果缺少 'industry' 字段: {result}")
            return None

        logger.info(
            f"[Analyzer] 行业分析完成：{result.get('industry')} - "
            f"{result.get('sub_industry', '未知')} "
            f"(置信度: {result.get('confidence', '?')})"
        )

        return result

    def _generate_recipe(
        self,
        industry_result: dict,
        section_titles: list[str],
    ) -> ReviewRecipe | None:
        """
        第二次 LLM 调用：根据行业生成审核配方

        参数：
            industry_result: 行业分析结果
            section_titles: 章节标题列表

        返回：
            ReviewRecipe 对象，失败返回 None
        """
        from config import config

        prompt = build_recipe_generation_prompt(
            industry=industry_result["industry"],
            sub_industry=industry_result.get("sub_industry", "通用"),
            section_titles=section_titles,
            available_dimensions=config.enabled_dimensions,
        )

        logger.info("[Analyzer] 开始生成审核配方...")

        result = self._llm_caller.call_json(prompt)

        if result is None:
            logger.warning("[Analyzer] 配方生成 LLM 调用失败")
            return None

        # 组装 ReviewRecipe
        try:
            return self._build_recipe(industry_result, result)
        except Exception as e:
            logger.error(f"[Analyzer] 配方组装失败: {e}")
            return None

    def _build_recipe(
        self,
        industry_result: dict,
        recipe_data: dict,
    ) -> ReviewRecipe:
        """
        把 LLM 返回的 JSON 组装成 ReviewRecipe 对象

        生活比喻：
        LLM 给了你一张手写的菜单（JSON dict），
        你要把它整理成标准格式的打印菜单（ReviewRecipe 对象）。

        参数：
            industry_result: 行业分析结果
            recipe_data: LLM 生成的配方 JSON

        返回：
            ReviewRecipe 对象
        """
        # 解析维度配置
        dimensions = []
        for dim_data in recipe_data.get("dimensions", []):
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
        for agent_data in recipe_data.get("agent_definitions", []):
            agent_def = AgentDefinition(
                agent_id=agent_data.get("agent_id", "unknown"),
                agent_name=agent_data.get("agent_name", "未知审核员"),
                dimension=agent_data.get("dimension", "未知"),
                description=agent_data.get("description", ""),
                skill_id=agent_data.get("skill_id", "unknown"),
            )
            agent_definitions.append(agent_def)

        return ReviewRecipe(
            industry=industry_result.get("industry", "通用"),
            sub_industry=industry_result.get("sub_industry", "通用"),
            confidence=industry_result.get("confidence", 0.5),
            dimensions=dimensions,
            agent_definitions=agent_definitions,
        )

    def _default_recipe(self) -> ReviewRecipe:
        """
        默认配方——当 LLM 分析失败时的兜底方案

        生活比喻：
        服务员判断不出客人想吃什么，就上今天的推荐套餐。
        虽然不一定完美，但至少不会让客人饿着。

        返回：
            包含四个默认维度的 ReviewRecipe
        """
        from config import config

        # 从配置中读取默认维度
        dimensions = []
        for key, dim_config in config.enabled_dimensions.items():
            dim = DimensionConfig(
                name=dim_config["name"],
                enabled=True,
                priority=dim_config.get("priority", "中"),
                focus_areas=[
                    f"检查{dim_config['name']}相关的所有要求是否满足",
                ],
                section_keywords=[],
            )
            dimensions.append(dim)

        # 默认 Agent 定义
        default_agents = [
            AgentDefinition(
                agent_id="completeness_agent",
                agent_name="完整性审核员",
                dimension="完整性",
                description="检查标书是否完整响应了所有招标要求",
                skill_id="completeness",
            ),
            AgentDefinition(
                agent_id="compliance_agent",
                agent_name="合规性审核员",
                dimension="合规性",
                description="检查标书是否符合法律法规和招标文件的合规要求",
                skill_id="compliance",
            ),
            AgentDefinition(
                agent_id="price_agent",
                agent_name="报价审核员",
                dimension="报价",
                description="检查报价是否合理、计算是否正确、有无遗漏项",
                skill_id="price",
            ),
            AgentDefinition(
                agent_id="risk_agent",
                agent_name="风险审核员",
                dimension="风险",
                description="检查标书中的潜在风险和不利条款",
                skill_id="risk",
            ),
        ]

        return ReviewRecipe(
            industry="通用",
            sub_industry="通用",
            confidence=0.3,
            dimensions=dimensions,
            agent_definitions=default_agents,
        )
