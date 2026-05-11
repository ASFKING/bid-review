# agents/agent_factory.py
# AgentFactory——根据审核配方（ReviewRecipe）动态创建审核 Agent
#
# 生活比喻：餐厅经理——接到今天的菜单（ReviewRecipe），
# 按菜单上的要求把对应的厨师（Agent）叫来，发好工牌，让他们各就各位。
#
# 核心设计：
#   输入：ReviewRecipe（来自 Analyzer 的分析结果）
#   输出：List[ReviewAgent]（一组配好对的审核员，可以直接干活）
#
# 为什么用工厂模式？
#   Analyzer 输出的 agent_definitions 里只有 skill_id 字符串（如 "completeness"），
#   但 ReviewAgent 需要的是一个真正的 Python 函数（如 build_completeness_prompt）。
#   AgentFactory 的职责就是：拿着 skill_id 去查表，找到对应的函数，创建 Agent。
#
#   好处：以后加新维度，只需要往 SKILL_REGISTRY 加一行，工厂逻辑完全不用动。

import logging
from typing import Callable

from models.schemas import ReviewRecipe, AgentDefinition
from agents.review_agent import ReviewAgent
from infrastructure.llm_caller import LLMCaller

# ===== Skill 注册表 =====
# skill_id → Prompt 构建函数 的映射
#
# 为什么用字典而不是 if-else？
#   1. 查找效率：字典 O(1)，if-else O(n)
#   2. 扩展性：加新维度只需加一行，不用改工厂逻辑
#   3. 可读性：一眼就能看到系统支持哪些 Skill
#
# 目前只有 completeness，其余在 Step 5.3 实现后补充
from prompts.completeness_skill import build_completeness_prompt

SKILL_REGISTRY: dict[str, Callable] = {
    "completeness": build_completeness_prompt,
    # 后续添加：
    # "compliance": build_compliance_prompt,
    # "price": build_price_prompt,
    # "risk": build_risk_prompt,
}

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Agent 工厂——根据 ReviewRecipe 创建审核 Agent 列表

    生活比喻：餐厅经理——看菜单（ReviewRecipe），
    叫来对应的厨师（Agent），发好工牌（绑定 Skill），安排上岗。

    用法：
        factory = AgentFactory(llm_caller)
        agents = factory.create_agents(recipe)
        # agents 是一个 List[ReviewAgent]，可以直接调用 review_document()
    """

    def __init__(self, llm_caller: LLMCaller):
        """
        初始化工厂

        参数：
            llm_caller: LLM 调用包装器（所有 Agent 共享同一个实例）
        """
        self._llm_caller = llm_caller

    def create_agents(self, recipe: ReviewRecipe) -> list[ReviewAgent]:
        """
        根据审核配方创建 Agent 列表

        流程：
        1. 遍历 recipe.agent_definitions（Analyzer 告诉我们需要哪些 Agent）
        2. 对每个 AgentDefinition，根据 skill_id 查找对应的 Skill 函数
        3. 创建 ReviewAgent 实例（绑定名称、维度、Skill、LLM）
        4. 返回 Agent 列表

        参数：
            recipe: Analyzer 生成的审核配方

        返回：
            List[ReviewAgent]——一组配好对的审核 Agent
        """
        agents: list[ReviewAgent] = []

        for agent_def in recipe.agent_definitions:
            agent = self._create_single_agent(agent_def)
            if agent is not None:
                agents.append(agent)

        logger.info(
            f"[AgentFactory] 根据配方创建了 {len(agents)} 个 Agent："
            f"{[a._agent_name for a in agents]}"
        )

        return agents

    def _create_single_agent(self, agent_def: AgentDefinition) -> ReviewAgent | None:
        """
        创建单个 Agent

        流程：
        1. 根据 skill_id 查找 Skill 函数
        2. 确定 Issue ID 前缀（如 "CP" 对应完整性）
        3. 创建 ReviewAgent 实例

        参数：
            agent_def: Agent 定义（来自 ReviewRecipe）

        返回：
            ReviewAgent 实例，失败返回 None
        """
        # ---- 第一步：查找 Skill 函数 ----
        skill_builder = self._get_skill_builder(agent_def.skill_id)

        if skill_builder is None:
            logger.warning(
                f"[AgentFactory] 跳过 Agent '{agent_def.agent_name}'："
                f"找不到 skill_id='{agent_def.skill_id}' 对应的 Skill"
            )
            return None

        # ---- 第二步：确定 Issue ID 前缀 ----
        # 从 Skill 注册表的维度名映射到缩写
        from prompts.structured_output_prompt import get_dimension_abbreviation
        id_prefix = get_dimension_abbreviation(agent_def.dimension)

        # ---- 第三步：创建 ReviewAgent ----
        agent = ReviewAgent(
            agent_name=agent_def.agent_name,
            dimension=agent_def.dimension,
            skill_builder=skill_builder,
            llm_caller=self._llm_caller,
            id_prefix=id_prefix,
        )

        logger.info(
            f"[AgentFactory] 创建 Agent：{agent_def.agent_name} "
            f"(维度={agent_def.dimension}, Skill={agent_def.skill_id}, "
            f"ID前缀={id_prefix})"
        )

        return agent

    def _get_skill_builder(self, skill_id: str) -> Callable | None:
        """
        根据 skill_id 查找对应的 Skill 构建函数

        参数：
            skill_id: Skill 标识符，如 "completeness"

        返回：
            对应的 Prompt 构建函数，找不到返回 None
        """
        return SKILL_REGISTRY.get(skill_id)
